"""
Bridge module for Aerofly FS4 IGC Recorder.
Coordinates all main components and provides a unified API.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Union, List, Tuple
import time
import datetime

from ..data.parser import ForeFlightParser, parser as default_parser
from ..io.udp import UDPServer, create_udp_server
from ..io.igc import IGCWriter, create_igc_writer
from .recorder import FlightRecorder, create_flight_recorder
from ..utils.events import EventType, Event, event_bus, publish_event
from ..config.settings import settings
from ..data.models import XGPSData, XATTData, ForeFlightData, DataType

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.core.bridge")


class AeroflyBridge:
    """
    High-level orchestrator that coordinates all components.
    Provides a unified API for the UI layer.
    """

    def __init__(self,
                 parser: Optional[ForeFlightParser] = None,
                 udp_port: Optional[int] = None,
                 udp_server: Optional[UDPServer] = None,
                 igc_writer: Optional[IGCWriter] = None):
        """
        Initialize the Aerofly bridge.

        Args:
            parser: Optional parser instance (uses default if None)
            udp_port: Optional UDP port (uses settings if None)
            udp_server: Optional UDP server instance (creates one if None)
            igc_writer: Optional IGC writer instance (creates one if None)
        """
        # Use default parser if none provided
        self.parser = parser or default_parser

        # Get UDP port from settings if not provided
        self.udp_port = udp_port or settings.get('udp_port')

        # Create components
        self.udp_server = udp_server or create_udp_server(self.parser, self.udp_port)
        self.igc_writer = igc_writer or create_igc_writer()
        self.flight_recorder = create_flight_recorder()

        # State tracking
        self.running = False
        self.event_tasks = []

        # Last received data
        self.last_gps_data: Optional[XGPSData] = None
        self.last_att_data: Optional[XATTData] = None
        self.last_data_time = 0

        logger.info(f"Aerofly Bridge initialized with UDP port {self.udp_port}")

    async def start(self) -> bool:
        """
        Start all components and the bridge.

        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.running:
            logger.warning("Aerofly Bridge already running")
            return False

        try:
            # Start UDP server
            udp_success = await self.udp_server.start()
            if not udp_success:
                logger.error("Failed to start UDP server")
                return False

            # Start flight recorder
            recorder_success = await self.flight_recorder.start()
            if not recorder_success:
                logger.error("Failed to start flight recorder")
                # Clean up UDP server
                await self.udp_server.stop()
                return False

            # Subscribe to events
            self.event_tasks.append(
                asyncio.create_task(
                    self._subscribe_to_events()
                )
            )

            self.running = True
            logger.info("Aerofly Bridge started")

            # Publish startup event
            await publish_event(
                EventType.UI_INITIALIZED,
                {
                    'message': 'Aerofly Bridge started and ready'
                },
                'AeroflyBridge'
            )

            return True

        except Exception as e:
            logger.error(f"Error starting Aerofly Bridge: {e}")

            # Clean up any started components
            await self._cleanup()

            return False

    async def stop(self) -> bool:
        """
        Stop all components and the bridge.

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        if not self.running:
            logger.warning("Aerofly Bridge not running")
            return True  # Return True since it's already stopped

        try:
            await self._cleanup()

            self.running = False
            logger.info("Aerofly Bridge stopped")

            return True

        except Exception as e:
            logger.error(f"Error stopping Aerofly Bridge: {e}")
            return False

    async def _cleanup(self) -> None:
        """Clean up all resources."""
        # Stop recorder first
        try:
            if self.flight_recorder:
                await self.flight_recorder.stop()
        except Exception as e:
            logger.error(f"Error stopping flight recorder: {e}")

        # Stop UDP server
        try:
            if self.udp_server:
                await self.udp_server.stop()
        except Exception as e:
            logger.error(f"Error stopping UDP server: {e}")

        # Cancel event tasks
        for task in self.event_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.event_tasks.clear()

    async def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events."""
        try:
            # Subscribe to error events
            await event_bus.subscribe(
                EventType.ERROR_OCCURRED,
                self._handle_error_event
            )

            # Subscribe to shutdown events
            await event_bus.subscribe(
                EventType.SHUTDOWN_REQUESTED,
                self._handle_shutdown_event
            )

            logger.debug("Subscribed to bridge events")

        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            raise

    async def _handle_error_event(self, event: Event) -> None:
        """Handle error events."""
        if not event.data:
            return

        # Log the error
        message = event.data.get('message', 'Unknown error')
        component = event.data.get('component', 'Unknown')

        logger.error(f"Error in {component}: {message}")

    async def _handle_shutdown_event(self, event: Event) -> None:
        """Handle shutdown request events."""
        logger.info("Shutdown requested, stopping bridge")
        await self.stop()

    async def start_recording(self,
                              pilot_name: str = "",
                              glider_type: str = "",
                              glider_id: str = "",
                              glider_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        Start recording flight data.

        Args:
            pilot_name: Name of the pilot
            glider_type: Type of glider/aircraft
            glider_id: Registration or ID of the glider
            glider_info: Additional glider information

        Returns:
            bool: True if recording started successfully, False otherwise
        """
        if not self.running:
            logger.warning("Aerofly Bridge not running")
            return False

        # Check if already recording using the recorder's status
        if self.get_recording_status().get('recording', {}).get('recording', False):
            logger.warning("Already recording")
            return False

        try:
            # Start recording through the flight recorder
            filename = await self.flight_recorder.start_recording(
                pilot_name=pilot_name,
                glider_type=glider_type,
                glider_id=glider_id,
                glider_info=glider_info
            )

            if filename:
                logger.info(f"Started recording to {filename}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            return False

    async def stop_recording(self) -> Union[str, None]:
        """
        Stop recording the current flight.

        Returns:
            Union[str, None]: Path to the IGC file if successful, None otherwise
        """
        if not self.running:
            logger.warning("Aerofly Bridge not running")
            return None

        return await self.flight_recorder.stop_recording()

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get the connection status with Aerofly FS4.

        Returns:
            Dict[str, Any]: Dictionary with connection status information
        """
        if not self.running:
            return {
                'running': False,
                'message': 'Bridge not running'
            }

        # Get status from UDP server
        return self.udp_server.get_connection_status()

    def get_recording_status(self) -> Dict[str, Any]:
        """
        Get the current recording status.

        Returns:
            Dict[str, Any]: Dictionary with recording status information
        """
        if not self.running:
            return {
                'running': False,
                'recording': False,
                'message': 'Bridge not running'
            }

        # Get status from flight recorder
        return self.flight_recorder.get_status()

    def get_status(self) -> Dict[str, Any]:
        """
        Get the overall status of the bridge and all components.

        Returns:
            Dict[str, Any]: Dictionary with status information
        """
        status = {
            'running': self.running,
            'uptime': 0,  # Will be set if running
            'components': {
                'udp_server': {
                    'running': self.udp_server.is_running
                },
                'flight_recorder': {
                    'running': self.flight_recorder.running if hasattr(self.flight_recorder, 'running') else False
                }
            }
        }

        # Add connection status
        status['connection'] = self.get_connection_status()

        # Add recording status
        status['recording'] = self.get_recording_status()

        return status

    async def run(self):
        """
        Run the bridge to receive and process UDP data.
        """
        try:
            await self._setup_udp()
            await self._receive_loop()
        except Exception as e:
            logger.error(f"Error in bridge: {e}")
            raise


# Factory function to create a bridge instance
def create_bridge(parser: Optional[ForeFlightParser] = None, udp_port: Optional[int] = None) -> AeroflyBridge:
    """
    Create a new bridge instance.

    Args:
        parser: Optional parser instance (uses default if None)
        udp_port: Optional UDP port (uses settings if None)

    Returns:
        AeroflyBridge: A new bridge instance
    """
    return AeroflyBridge(parser, udp_port)


# Coroutine to run the bridge directly (for testing or CLI mode)
async def run_bridge() -> None:
    """
    Run the bridge directly until interrupted.
    Used for testing or CLI mode.
    """
    # Create and start bridge
    bridge = create_bridge()
    await bridge.start()

    try:
        # Run forever until interrupted
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        # Handle cancellation
        logger.info("Bridge run cancelled")
    except Exception as e:
        logger.error(f"Error running bridge: {e}")
    finally:
        # Clean up
        await bridge.stop()