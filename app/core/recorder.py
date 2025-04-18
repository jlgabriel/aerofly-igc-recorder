"""
Flight Recorder core component for Aerofly FS4 IGC Recorder.
Coordinates receiving flight data and writing to IGC files.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Union, Tuple
import datetime
import time

from ..data.models import XGPSData, XATTData, ForeFlightData, DataType
from ..io.igc import IGCWriter, create_igc_writer
from ..utils.events import EventType, Event, publish_event, event_bus
from ..config.settings import settings

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.core.recorder")


class FlightRecorder:
    """
    Core component that coordinates flight data recording.
    Listens for flight data events and writes them to IGC files.
    """

    def __init__(self, igc_writer: Optional[IGCWriter] = None):
        """
        Initialize the flight recorder.
        
        Args:
            igc_writer: Optional IGC writer instance (creates one if None)
        """
        # Create or use provided IGC writer
        self.igc_writer = igc_writer or create_igc_writer()
        
        # Data storage for latest position and attitude
        self.latest_gps_data: Optional[XGPSData] = None
        self.latest_att_data: Optional[XATTData] = None
        
        # Recording configuration
        self.recording_interval = settings.get('recording_interval', 1.0)  # seconds
        self.last_record_time = 0
        
        # Event subscription tasks
        self.event_tasks = []
        self.running = False
        
        # Queue for position data (to handle high-frequency updates)
        self.position_queue = asyncio.Queue()
        self.queue_processor_task = None
        
        logger.info("Flight Recorder initialized")

    async def start(self) -> bool:
        """
        Start the recorder and subscribe to events.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        if self.running:
            logger.warning("Flight Recorder already running")
            return False
            
        try:
            # Subscribe to data events
            self.event_tasks.append(
                asyncio.create_task(
                    self._subscribe_to_events()
                )
            )
            
            # Start queue processor
            self.queue_processor_task = asyncio.create_task(
                self._process_position_queue()
            )
            
            self.running = True
            logger.info("Flight Recorder started")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting Flight Recorder: {e}")
            await self._cleanup_tasks()
            return False

    async def stop(self) -> bool:
        """
        Stop the recorder and unsubscribe from events.
        
        Returns:
            bool: True if stopped successfully, False otherwise
        """
        if not self.running:
            logger.warning("Flight Recorder not running")
            return False
            
        try:
            # Stop recording if active
            if self.igc_writer.recording:
                await self.stop_recording()
                
            # Clean up tasks
            await self._cleanup_tasks()
            
            self.running = False
            logger.info("Flight Recorder stopped")
            
            return True
            
        except Exception as e:
            logger.error(f"Error stopping Flight Recorder: {e}")
            return False

    async def _cleanup_tasks(self) -> None:
        """Cancel and clean up all tasks."""
        # Cancel event subscription tasks
        for task in self.event_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        self.event_tasks.clear()
        
        # Cancel queue processor task
        if self.queue_processor_task and not self.queue_processor_task.done():
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
                
        self.queue_processor_task = None

    async def _subscribe_to_events(self) -> None:
        """Subscribe to data received events."""
        try:
            # Subscribe to data received events
            await event_bus.subscribe(
                EventType.DATA_RECEIVED,
                self._handle_data_event
            )
            
            logger.debug("Subscribed to DATA_RECEIVED events")
            
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            raise

    async def _handle_data_event(self, event: Event) -> None:
        """
        Handle data received events.
        
        Args:
            event: The data event
        """
        try:
            if not event.data or 'data' not in event.data:
                return
                
            data_dict = event.data['data']
            data_type = data_dict.get('type')
            
            if data_type == DataType.GPS.value:
                # Create XGPSData from dict
                timestamp = None
                if 'timestamp' in data_dict and data_dict['timestamp']:
                    try:
                        timestamp = datetime.datetime.fromisoformat(data_dict['timestamp'])
                    except (ValueError, TypeError):
                        pass
                        
                gps_data = XGPSData(
                    sim_name=data_dict.get('sim_name', ''),
                    longitude=data_dict.get('longitude', 0.0),
                    latitude=data_dict.get('latitude', 0.0),
                    alt_msl_meters=data_dict.get('alt_msl_meters', 0.0),
                    track_deg=data_dict.get('track_deg', 0.0),
                    ground_speed_mps=data_dict.get('ground_speed_mps', 0.0),
                    timestamp=timestamp
                )
                
                # Store latest GPS data
                self.latest_gps_data = gps_data
                
                # Add to position queue if recording
                if self.igc_writer.recording:
                    await self._queue_position(gps_data, self.latest_att_data)
                    
            elif data_type == DataType.ATTITUDE.value:
                # Create XATTData from dict
                timestamp = None
                if 'timestamp' in data_dict and data_dict['timestamp']:
                    try:
                        timestamp = datetime.datetime.fromisoformat(data_dict['timestamp'])
                    except (ValueError, TypeError):
                        pass
                        
                att_data = XATTData(
                    sim_name=data_dict.get('sim_name', ''),
                    heading_deg=data_dict.get('heading_deg', 0.0),
                    pitch_deg=data_dict.get('pitch_deg', 0.0),
                    roll_deg=data_dict.get('roll_deg', 0.0),
                    timestamp=timestamp
                )
                
                # Store latest attitude data
                self.latest_att_data = att_data
                
        except Exception as e:
            logger.error(f"Error handling data event: {e}")

    async def _queue_position(self, gps_data: XGPSData, att_data: Optional[XATTData] = None) -> None:
        """
        Queue a position for recording with rate limiting.
        
        Args:
            gps_data: GPS position data
            att_data: Optional attitude data
        """
        current_time = time.time()
        
        # Check if it's time to record a new position
        if (self.last_record_time == 0 or 
                current_time - self.last_record_time >= self.recording_interval):
            
            # Update last record time
            self.last_record_time = current_time
            
            # Add to queue
            await self.position_queue.put((gps_data, att_data))

    async def _process_position_queue(self) -> None:
        """Process the position queue in the background."""
        try:
            while True:
                # Get item from queue
                gps_data, att_data = await self.position_queue.get()
                
                # Process item
                if self.igc_writer.recording:
                    await self.igc_writer.add_position(gps_data, att_data)
                
                # Mark item as done
                self.position_queue.task_done()
                
                # Small sleep to avoid consuming too much CPU
                await asyncio.sleep(0.01)
                
        except asyncio.CancelledError:
            logger.debug("Position queue processor cancelled")
            raise
            
        except Exception as e:
            logger.error(f"Error in position queue processor: {e}")

    async def start_recording(self, 
                        pilot_name: str = "", 
                        glider_type: str = "", 
                        glider_id: str = "") -> Union[str, None]:
        """
        Start recording a flight.
        
        Args:
            pilot_name: Name of the pilot
            glider_type: Type of glider/aircraft
            glider_id: Registration or ID of the glider
            
        Returns:
            Union[str, None]: Path to the IGC file if successful, None otherwise
        """
        if not self.running:
            logger.warning("Flight Recorder not running")
            return None
            
        if self.igc_writer.recording:
            logger.warning("Already recording")
            return None
            
        # Reset last record time
        self.last_record_time = 0
        
        # Start recording
        return await self.igc_writer.start_recording(
            pilot_name=pilot_name,
            glider_type=glider_type,
            glider_id=glider_id
        )

    async def stop_recording(self) -> Union[str, None]:
        """
        Stop recording the current flight.
        
        Returns:
            Union[str, None]: Path to the IGC file if successful, None otherwise
        """
        if not self.running:
            logger.warning("Flight Recorder not running")
            return None
            
        if not self.igc_writer.recording:
            logger.warning("Not recording")
            return None
            
        # Process any remaining items in the queue
        if not self.position_queue.empty():
            try:
                while not self.position_queue.empty():
                    gps_data, att_data = await self.position_queue.get()
                    await self.igc_writer.add_position(gps_data, att_data)
                    self.position_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing remaining queue items: {e}")
        
        # Stop recording
        return await self.igc_writer.stop_recording()

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the recorder.
        
        Returns:
            Dict[str, Any]: Dictionary with status information
        """
        status = {
            'running': self.running,
            'queue_size': self.position_queue.qsize() if self.position_queue else 0
        }
        
        # Add recording status
        if self.igc_writer:
            status['recording'] = self.igc_writer.get_recording_status()
            
        # Add latest position if available
        if self.latest_gps_data:
            status['latest_position'] = {
                'latitude': self.latest_gps_data.latitude,
                'longitude': self.latest_gps_data.longitude,
                'altitude': self.latest_gps_data.alt_msl_meters,
                'speed': self.latest_gps_data.ground_speed_mps,
                'track': self.latest_gps_data.track_deg,
                'timestamp': self.latest_gps_data.timestamp.isoformat() 
                    if self.latest_gps_data.timestamp else None
            }
            
        # Add latest attitude if available
        if self.latest_att_data:
            status['latest_attitude'] = {
                'heading': self.latest_att_data.heading_deg,
                'pitch': self.latest_att_data.pitch_deg,
                'roll': self.latest_att_data.roll_deg,
                'timestamp': self.latest_att_data.timestamp.isoformat() 
                    if self.latest_att_data.timestamp else None
            }
            
        return status


# Factory function to create a flight recorder
def create_flight_recorder(igc_writer: Optional[IGCWriter] = None) -> FlightRecorder:
    """
    Create a new flight recorder instance.
    
    Args:
        igc_writer: Optional IGC writer instance (creates one if None)
        
    Returns:
        FlightRecorder: A new flight recorder instance
    """
    return FlightRecorder(igc_writer)
