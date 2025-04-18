"""
UDP Server module for Aerofly FS4 IGC Recorder.
Listens for ForeFlight-compatible data on UDP port (default: 49002).
"""

import socket
import asyncio
import logging
import time
from typing import Optional, Tuple, Callable, Any
import datetime

from ..data.models import ForeFlightData
from ..data.parser import ForeFlightParser
from ..config.constants import DEFAULT_UDP_PORT, DEFAULT_BUFFER_SIZE, DEFAULT_ENCODING
from ..config.settings import settings
from ..utils.events import EventType, publish_event, event_bus

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.io.udp")


class UDPServer:
    """
    UDP Server that listens for ForeFlight-compatible data from Aerofly FS4.
    Parses incoming data and publishes events when data is received.
    """

    def __init__(self, parser: ForeFlightParser, port: Optional[int] = None):
        """
        Initialize the UDP server.
        
        Args:
            parser: Parser to use for incoming data
            port: UDP port to listen on (default: from settings)
        """
        self.parser = parser
        self.port = port or settings.get('udp_port', DEFAULT_UDP_PORT)
        self.socket = None
        self.receive_task = None
        self.running = False
        self.last_data_time = None
        
        # Keep track of latest data received
        self.latest_gps_data = None
        self.latest_att_data = None
        
        logger.info(f"UDP Server initialized on port {self.port}")

    async def start(self) -> bool:
        """
        Start the UDP server.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.running:
            logger.warning("UDP Server already running")
            return False
            
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Enable broadcast & address reuse
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Set blocking to True since we'll run in a separate task
            self.socket.setblocking(True)
            
            # Bind to all interfaces on the specified port
            self.socket.bind(('0.0.0.0', self.port))
            
            logger.info(f"UDP Server listening on port {self.port}")
            
            # Start receiving task
            self.running = True
            self.receive_task = asyncio.create_task(self._receive_loop())
            
            # Publish event
            await publish_event(
                EventType.CONNECTION_ESTABLISHED,
                {
                    'type': 'udp',
                    'port': self.port
                },
                'UDPServer'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting UDP Server: {e}")
            
            # Clean up if error occurs
            if self.socket:
                self.socket.close()
                self.socket = None
                
            self.running = False
            
            # Publish error event
            await publish_event(
                EventType.ERROR_OCCURRED,
                {
                    'message': f"Failed to start UDP Server: {str(e)}",
                    'component': 'UDPServer'
                },
                'UDPServer'
            )
            
            return False

    async def stop(self) -> bool:
        """
        Stop the UDP server.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        if not self.running:
            logger.warning("UDP Server not running")
            return False
            
        try:
            # Stop the server
            self.running = False
            
            # Cancel receive task
            if self.receive_task:
                self.receive_task.cancel()
                try:
                    await self.receive_task
                except asyncio.CancelledError:
                    pass
                self.receive_task = None
            
            # Close socket
            if self.socket:
                self.socket.close()
                self.socket = None
                
            logger.info("UDP Server stopped")
            
            # Publish event
            await publish_event(
                EventType.CONNECTION_LOST,
                {
                    'type': 'udp',
                    'port': self.port
                },
                'UDPServer'
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping UDP Server: {e}")
            
            # Publish error event
            await publish_event(
                EventType.ERROR_OCCURRED,
                {
                    'message': f"Failed to stop UDP Server: {str(e)}",
                    'component': 'UDPServer'
                },
                'UDPServer'
            )
            
            return False

    async def _receive_loop(self) -> None:
        """
        Main receive loop for UDP data.
        Runs in a separate task and processes incoming data.
        """
        logger.debug("UDP receive loop started")
        
        try:
            while self.running:
                try:
                    # Receive data (will block until data arrives)
                    # Use asyncio.to_thread to avoid blocking the event loop
                    data, addr = await asyncio.to_thread(
                        self.socket.recvfrom, 
                        DEFAULT_BUFFER_SIZE
                    )
                    
                    # Process the data
                    await self._process_data(data, addr)
                    
                except (ConnectionError, OSError) as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                        
                        # Attempt to reconnect after error
                        await asyncio.sleep(1)
                        continue
                    else:
                        # Server is shutting down
                        break
                        
                except asyncio.CancelledError:
                    # Task is being cancelled
                    logger.debug("UDP receive task cancelled")
                    break
                    
                except Exception as e:
                    logger.error(f"Error in UDP receive loop: {e}")
                    
                    # Publish error event
                    await publish_event(
                        EventType.ERROR_OCCURRED,
                        {
                            'message': f"UDP receive error: {str(e)}",
                            'component': 'UDPServer'
                        },
                        'UDPServer'
                    )
                    
                    # Continue despite errors
                    await asyncio.sleep(0.1)
                    
        finally:
            logger.debug("UDP receive loop ended")
            
            # Make sure socket is closed
            if self.socket and self.running:
                try:
                    self.socket.close()
                    self.socket = None
                except Exception as e:
                    logger.error(f"Error closing socket: {e}")

    async def _process_data(self, data: bytes, addr: Tuple[str, int]) -> None:
        """
        Process received UDP data.
        
        Args:
            data: Raw data received
            addr: Address (IP, port) of the sender
        """
        if not data:
            return
            
        try:
            # Update last data time
            current_time = time.time()
            first_data = self.last_data_time is None
            self.last_data_time = current_time
            
            # If this is the first data received or it's been a while,
            # log connection information
            if first_data:
                logger.info(f"First data received from {addr[0]}:{addr[1]}")
                
            # Decode the data
            line = data.decode(DEFAULT_ENCODING, errors='ignore').strip()
            
            # Parse the data
            timestamp = datetime.datetime.now(datetime.timezone.utc)
            parsed_data = self.parser.parse_line(line, timestamp)
            
            # Update latest data based on type
            from ..data.models import XGPSData, XATTData
            if isinstance(parsed_data, XGPSData):
                self.latest_gps_data = parsed_data
            elif isinstance(parsed_data, XATTData):
                self.latest_att_data = parsed_data
                
            # Publish data received event
            await publish_event(
                EventType.DATA_RECEIVED,
                {
                    'data': parsed_data.to_dict(),
                    'raw': line,
                    'source': addr
                },
                'UDPServer'
            )
            
            # Log sample data periodically
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Received data: {line}")
                logger.debug(f"Parsed as: {parsed_data}")
                
        except Exception as e:
            logger.error(f"Error processing UDP data: {e}")
            
            # Publish error event
            await publish_event(
                EventType.ERROR_OCCURRED,
                {
                    'message': f"Error processing UDP data: {str(e)}",
                    'component': 'UDPServer',
                    'raw_data': data.decode(DEFAULT_ENCODING, errors='ignore') if isinstance(data, bytes) else str(data)
                },
                'UDPServer'
            )

    @property
    def is_running(self) -> bool:
        """Get the running state of the server"""
        return self.running

    @property
    def has_connection(self) -> bool:
        """
        Check if the server has recently received data.
        
        Returns:
            bool: True if data was received in the last 5 seconds
        """
        if self.last_data_time is None:
            return False
            
        # Check if data was received within the timeout period
        timeout = settings.get('connection_timeout', 5.0)
        return (time.time() - self.last_data_time) < timeout
        
    def get_connection_status(self) -> dict:
        """
        Get the current connection status.
        
        Returns:
            dict: Dictionary with connection status information
        """
        current_time = time.time()
        
        status = {
            'running': self.running,
            'port': self.port,
            'has_connection': self.has_connection
        }
        
        # Add time since last data if applicable
        if self.last_data_time is not None:
            status['last_data_seconds_ago'] = current_time - self.last_data_time
            status['last_data_time'] = datetime.datetime.fromtimestamp(
                self.last_data_time
            ).strftime('%H:%M:%S')
            
        # Add latest data summary if available
        if self.latest_gps_data:
            status['has_gps_data'] = True
            status['latest_position'] = {
                'latitude': self.latest_gps_data.latitude,
                'longitude': self.latest_gps_data.longitude,
                'altitude': self.latest_gps_data.alt_msl_meters,
                'speed': self.latest_gps_data.ground_speed_mps,
                'track': self.latest_gps_data.track_deg
            }
        else:
            status['has_gps_data'] = False
            
        if self.latest_att_data:
            status['has_attitude_data'] = True
            status['latest_attitude'] = {
                'heading': self.latest_att_data.heading_deg,
                'pitch': self.latest_att_data.pitch_deg,
                'roll': self.latest_att_data.roll_deg
            }
        else:
            status['has_attitude_data'] = False
            
        return status


# Create a factory function to get a UDP server instance
# This allows for easier testing and dependency injection
def create_udp_server(parser: Optional[ForeFlightParser] = None, port: Optional[int] = None) -> UDPServer:
    """
    Create a new UDP server instance.
    
    Args:
        parser: Parser to use (if None, uses default instance)
        port: UDP port to listen on (default: from settings)
        
    Returns:
        UDPServer: A new UDP server instance
    """
    # Use default parser if none provided
    if parser is None:
        from ..data.parser import parser as default_parser
        parser = default_parser
        
    return UDPServer(parser, port)
