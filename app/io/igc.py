"""
IGC File writer module for Aerofly FS4 IGC Recorder.
Handles writing flight data to IGC files using the aerofiles library.
"""

import os
import logging
import datetime
from typing import Optional, Dict, List, Any, TextIO, Union
from pathlib import Path
import asyncio

# Import aerofiles for IGC file handling
try:
    from aerofiles.igc import Writer
except ImportError:
    logging.error("aerofiles library not found. Please install with: pip install aerofiles")
    raise

from ..data.models import XGPSData, XATTData
from ..config.constants import IGC_EXTENSION, IGC_MANUFACTURER_CODE, IGC_LOGGER_ID
from ..config.settings import settings
from ..utils.events import EventType, publish_event

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.io.igc")


class IGCWriter:
    """
    Handles writing flight data to IGC files.
    Uses aerofiles library for IGC format compliance.
    """

    def __init__(self):
        """Initialize the IGC writer."""
        self._lock = asyncio.Lock()
        self.reset()
        
    def reset(self):
        """Reset the writer state."""
        self.file = None
        self.writer = None
        self.filename = None
        self.pilot_name = None
        self.glider_type = None
        self.glider_id = None
        self.recording = False
        self.start_time = None
        self.end_time = None
        self.fix_count = 0
        self.second_counter = 0

    async def start_recording(self, 
                       pilot_name: str = "", 
                       glider_type: str = "", 
                       glider_id: str = "",
                       igc_directory: Optional[str] = None) -> Union[str, None]:
        """
        Start recording a new IGC file.
        
        Args:
            pilot_name: Name of the pilot
            glider_type: Type of glider/aircraft
            glider_id: Registration or ID of the glider
            igc_directory: Directory to save the IGC file (default: from settings)
            
        Returns:
            str: Path to the IGC file if successful, None otherwise
        """
        async with self._lock:
            if self.recording:
                logger.warning("Already recording an IGC file")
                return None
                
            try:
                # Get the output directory
                if igc_directory is None:
                    igc_directory = settings.get('igc_directory')
                    
                # Create the directory if it doesn't exist
                os.makedirs(igc_directory, exist_ok=True)
                
                # Generate filename
                self.filename = os.path.join(igc_directory, self._generate_filename())
                
                # Store metadata
                self.pilot_name = pilot_name or settings.get('default_pilot_name', "Simulator Pilot")
                self.glider_type = glider_type or settings.get('default_glider_type', "Aerofly FS4")
                self.glider_id = glider_id or settings.get('default_glider_id', "SIM")
                
                # Open file for writing in binary mode (required by aerofiles)
                self.file = open(self.filename, 'wb')
                
                # Create aerofiles IGC writer
                self.writer = Writer(self.file)
                
                # Get current time as UTC
                self.start_time = datetime.datetime.now(datetime.timezone.utc)
                
                # Initialize seconds counter for time simulation
                self.second_counter = 0
                
                # Write IGC header records
                self._write_header()
                
                # Reset fix count
                self.fix_count = 0
                
                # Set recording flag
                self.recording = True
                
                logger.info(f"Started recording IGC file: {self.filename}")
                
                # Publish event
                await publish_event(
                    EventType.RECORDING_STARTED,
                    {
                        'filename': self.filename,
                        'pilot_name': self.pilot_name,
                        'glider_type': self.glider_type,
                        'glider_id': self.glider_id,
                        'start_time': self.start_time.isoformat()
                    },
                    'IGCWriter'
                )
                
                return self.filename
                
            except Exception as e:
                logger.error(f"Error starting IGC recording: {e}")
                
                # Clean up if error occurs
                if hasattr(self, 'file') and self.file:
                    self.file.close()
                
                self.reset()
                
                # Publish error event
                await publish_event(
                    EventType.ERROR_OCCURRED,
                    {
                        'message': f"Failed to start IGC recording: {str(e)}",
                        'component': 'IGCWriter'
                    },
                    'IGCWriter'
                )
                
                return None

    async def stop_recording(self) -> Union[str, None]:
        """
        Stop recording and close the IGC file.
        
        Returns:
            str: Path to the IGC file if successful, None otherwise
        """
        async with self._lock:
            if not self.recording:
                logger.warning("Not recording an IGC file")
                return None
                
            try:
                # Set end time
                self.end_time = datetime.datetime.now(datetime.timezone.utc)
                
                # Write final comments
                if self.writer:
                    try:
                        self.writer.write_comment(
                            "END", 
                            f"Recording ended at {self.end_time.strftime('%H:%M:%S')}"
                        )
                    except Exception as e:
                        logger.error(f"Error writing end comment: {e}")
                
                # Close the file
                if self.file:
                    self.file.close()
                    self.file = None
                
                # Check if any fixes were recorded
                if self.fix_count > 0:
                    logger.info(f"Stopped recording. Wrote {self.fix_count} fixes to {self.filename}")
                    
                    # Store the filename before resetting
                    result_file = self.filename
                    
                    # Publish event
                    await publish_event(
                        EventType.RECORDING_STOPPED,
                        {
                            'filename': result_file,
                            'fix_count': self.fix_count,
                            'duration_seconds': (self.end_time - self.start_time).total_seconds(),
                            'end_time': self.end_time.isoformat()
                        },
                        'IGCWriter'
                    )
                    
                    # Reset the writer state
                    self.reset()
                    
                    return result_file
                else:
                    logger.warning("No data was recorded, deleting empty IGC file")
                    
                    # Delete the empty file
                    if self.filename and os.path.exists(self.filename):
                        os.remove(self.filename)
                    
                    # Publish event
                    await publish_event(
                        EventType.RECORDING_STOPPED,
                        {
                            'filename': None,
                            'fix_count': 0,
                            'message': 'No data was recorded'
                        },
                        'IGCWriter'
                    )
                    
                    # Reset the writer state
                    self.reset()
                    
                    return None
                    
            except Exception as e:
                logger.error(f"Error stopping IGC recording: {e}")
                
                # Clean up even if error occurs
                if self.file:
                    try:
                        self.file.close()
                    except:
                        pass
                
                # Store the filename before resetting
                result_file = self.filename
                
                # Reset state
                self.reset()
                
                # Publish error event
                await publish_event(
                    EventType.ERROR_OCCURRED,
                    {
                        'message': f"Error stopping IGC recording: {str(e)}",
                        'component': 'IGCWriter'
                    },
                    'IGCWriter'
                )
                
                return result_file

    async def add_position(self, 
                    gps_data: XGPSData, 
                    att_data: Optional[XATTData] = None) -> bool:
        """
        Add a position fix to the IGC file.
        
        Args:
            gps_data: GPS position data
            att_data: Optional attitude data
            
        Returns:
            bool: True if position was added successfully, False otherwise
        """
        async with self._lock:
            if not self.recording or not self.file or not self.writer:
                return False
                
            try:
                # Extract data from GPS
                latitude = gps_data.latitude
                longitude = gps_data.longitude
                altitude = int(gps_data.alt_msl_meters)  # IGC uses meters
                
                # Get pressure altitude (we don't have this in simulator, use MSL as approximation)
                pressure_alt = altitude
                
                # For screen display, continue incrementing the seconds
                self.second_counter += 1
                
                # Calculate hours, minutes, and seconds properly
                total_seconds = self.second_counter
                hours = 12  # Start at 12:00:00
                minutes = (total_seconds // 60) % 60
                seconds = total_seconds % 60
                
                # Create a properly incremented time
                simulated_time = datetime.time(
                    hour=hours,
                    minute=minutes,
                    second=seconds,
                    microsecond=0
                )
                
                # Write B record (position fix) using aerofiles
                self.writer.write_fix(
                    time=simulated_time,  # Use simulated time that increases properly
                    latitude=latitude,
                    longitude=longitude,
                    valid=True,  # Mark as valid GPS fix
                    pressure_alt=pressure_alt,
                    gps_alt=altitude,
                    extensions = [50, 0]  # Optional extensions (e.g., GPS quality)
                )
                
                # Increment fix count
                self.fix_count += 1
                
                # Publish event (at a reduced rate to avoid flooding)
                if self.fix_count % 10 == 0:  # Only publish every 10th position
                    await publish_event(
                        EventType.POSITION_ADDED,
                        {
                            'fix_count': self.fix_count,
                            'position': {
                                'latitude': latitude,
                                'longitude': longitude,
                                'altitude': altitude
                            }
                        },
                        'IGCWriter'
                    )
                
                return True
                
            except Exception as e:
                logger.error(f"Error adding position to IGC file: {e}")
                
                # Publish error event
                await publish_event(
                    EventType.ERROR_OCCURRED,
                    {
                        'message': f"Error adding position to IGC file: {str(e)}",
                        'component': 'IGCWriter'
                    },
                    'IGCWriter'
                )
                
                return False

    def _write_header(self) -> bool:
        """
        Write the IGC file header.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Utilizamos write_headers para manejar todos los encabezados requeridos
            self.writer.write_headers({
                'manufacturer_code': IGC_MANUFACTURER_CODE,
                'logger_id': IGC_LOGGER_ID,
                'date': self.start_time.date(),
                'logger_type': 'Aerofly FS4 Simulator',
                'gps_receiver': 'SIMULATOR',
                'firmware_version': '1.0',
                'hardware_version': '1.0',
                'pilot': self.pilot_name,
                'glider_type': self.glider_type,
                'glider_id': self.glider_id,
                'gps_datum': 'WGS-1984',  # Añadimos el datum GPS
            })
            # Write the IGC file header
            self.writer.write_fix_extensions([('FXA', 3), ('ENL', 3)])

            # Add a comment about the source
            self.writer.write_comment("GEN", "Generated by Aerofly FS4 IGC Recorder")
            self.writer.write_comment("SIM", "Flight recorded in Aerofly FS4 simulator")
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing IGC header: {e}")
            return False

    def _generate_filename(self) -> str:
        """
        Generate a filename for the IGC file based on current date and time.
        
        Returns:
            str: Generated filename
        """
        now = datetime.datetime.now()
        return f"AEROFLY_{now.strftime('%Y%m%d_%H%M%S')}{IGC_EXTENSION}"

    def get_recording_status(self) -> Dict[str, Any]:
        """
        Get the current recording status.
        
        Returns:
            dict: Dictionary with recording status information
        """
        status = {
            'recording': self.recording,
            'fix_count': self.fix_count
        }
        
        if self.recording:
            status['filename'] = self.filename
            status['pilot_name'] = self.pilot_name
            status['glider_type'] = self.glider_type
            status['glider_id'] = self.glider_id
            
            if self.start_time:
                current_time = datetime.datetime.now(datetime.timezone.utc)
                duration = current_time - self.start_time
                status['duration_seconds'] = duration.total_seconds()
                hours, remainder = divmod(duration.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                status['duration_formatted'] = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
                status['start_time'] = self.start_time.isoformat()
                
        return status


# Create a factory function to get an IGC writer instance
def create_igc_writer() -> IGCWriter:
    """
    Create a new IGC writer instance.
    
    Returns:
        IGCWriter: A new IGC writer instance
    """
    return IGCWriter()
