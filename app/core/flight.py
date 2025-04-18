"""
Flight data management for Aerofly FS4 IGC Recorder.
Handles flight metadata, statistics, and analysis.
"""

import logging
import datetime
import json
import os
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
import statistics

from ..data.models import XGPSData, XATTData
from ..config.constants import METERS_TO_FEET, MPS_TO_KTS, MPS_TO_FPM
from ..config.settings import settings
from ..io.files import get_file_info, get_igc_directory

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.core.flight")


class FlightData:
    """
    Represents a flight with metadata and statistics.
    Can be created from an IGC file or live flight data.
    """

    def __init__(self, 
                 filename: Optional[str] = None,
                 pilot_name: str = "",
                 glider_type: str = "",
                 glider_id: str = ""):
        """
        Initialize a flight data object.
        
        Args:
            filename: Optional path to an IGC file
            pilot_name: Name of the pilot
            glider_type: Type of glider/aircraft
            glider_id: Registration or ID of the glider
        """
        # Basic flight metadata
        self.filename = filename
        self.pilot_name = pilot_name or settings.get('default_pilot_name', "Simulator Pilot")
        self.glider_type = glider_type or settings.get('default_glider_type', "Aerofly FS4")
        self.glider_id = glider_id or settings.get('default_glider_id', "SIM")
        
        # Flight timestamps
        self.start_time: Optional[datetime.datetime] = None
        self.end_time: Optional[datetime.datetime] = None
        
        # Flight statistics
        self.positions: List[XGPSData] = []
        self.attitudes: List[XATTData] = []
        self.distance_km: float = 0.0
        self.max_altitude_meters: float = 0.0
        self.min_altitude_meters: float = 0.0
        self.max_speed_mps: float = 0.0
        self.avg_speed_mps: float = 0.0
        
        # Derived data
        self._statistics_calculated = False
        self._metadata = {}
        
        # If filename is provided, load from file
        if filename and os.path.exists(filename):
            self._load_from_file(filename)

    def _load_from_file(self, filename: str) -> None:
        """
        Load flight data from an IGC file.
        
        Args:
            filename: Path to the IGC file
        """
        try:
            # Get file info
            file_info = get_file_info(filename)
            
            # TODO: Implement IGC file parsing
            # This would require reading and parsing the IGC file
            # and populating the flight data properties
            
            # For now, just log that we're not implementing this yet
            logger.info(f"Loading from IGC file not fully implemented yet: {filename}")
            
            # Set basic properties from file info
            self.filename = filename
            
            # Parse creation time from filename if possible
            if 'filename' in file_info:
                try:
                    # Extract date/time from typical format: AEROFLY_YYYYMMDD_HHMMSS.igc
                    basename = file_info['filename']
                    if basename.startswith('AEROFLY_') and len(basename) >= 21:
                        date_str = basename[8:16]  # YYYYMMDD
                        time_str = basename[17:23]  # HHMMSS
                        
                        # Parse into datetime
                        self.start_time = datetime.datetime.strptime(
                            f"{date_str}_{time_str}",
                            "%Y%m%d_%H%M%S"
                        )
                except Exception as e:
                    logger.error(f"Error parsing timestamp from filename: {e}")
            
            # If we couldn't get time from filename, use file creation time
            if not self.start_time and 'created' in file_info:
                try:
                    self.start_time = datetime.datetime.fromisoformat(file_info['created'])
                except Exception as e:
                    logger.error(f"Error parsing file creation time: {e}")
            
        except Exception as e:
            logger.error(f"Error loading flight data from file {filename}: {e}")

    def add_position(self, position: XGPSData) -> None:
        """
        Add a position fix to the flight data.
        
        Args:
            position: GPS position data
        """
        # Update start/end times
        if position.timestamp:
            if not self.start_time or position.timestamp < self.start_time:
                self.start_time = position.timestamp
            if not self.end_time or position.timestamp > self.end_time:
                self.end_time = position.timestamp
        
        # Add to positions list
        self.positions.append(position)
        
        # Mark that statistics need to be recalculated
        self._statistics_calculated = False

    def add_attitude(self, attitude: XATTData) -> None:
        """
        Add an attitude record to the flight data.
        
        Args:
            attitude: Aircraft attitude data
        """
        # Update start/end times
        if attitude.timestamp:
            if not self.start_time or attitude.timestamp < self.start_time:
                self.start_time = attitude.timestamp
            if not self.end_time or attitude.timestamp > self.end_time:
                self.end_time = attitude.timestamp
        
        # Add to attitudes list
        self.attitudes.append(attitude)

    def calculate_statistics(self) -> None:
        """Calculate various flight statistics from the position data."""
        if not self.positions or len(self.positions) < 2:
            logger.warning("Not enough positions to calculate statistics")
            return
            
        try:
            # Calculate altitude statistics
            altitudes = [pos.alt_msl_meters for pos in self.positions]
            self.max_altitude_meters = max(altitudes)
            self.min_altitude_meters = min(altitudes)
            
            # Calculate speed statistics
            speeds = [pos.ground_speed_mps for pos in self.positions]
            self.max_speed_mps = max(speeds)
            self.avg_speed_mps = statistics.mean(speeds) if speeds else 0
            
            # TODO: Calculate distance traveled
            # This requires calculating distances between consecutive points
            # using the haversine formula
            self.distance_km = 0.0  # Placeholder
            
            # Mark statistics as calculated
            self._statistics_calculated = True
            
        except Exception as e:
            logger.error(f"Error calculating flight statistics: {e}")

    def get_duration(self) -> Optional[datetime.timedelta]:
        """
        Get the flight duration.
        
        Returns:
            Optional[datetime.timedelta]: Flight duration, or None if unknown
        """
        if not self.start_time or not self.end_time:
            return None
            
        return self.end_time - self.start_time

    def get_duration_seconds(self) -> Optional[float]:
        """
        Get the flight duration in seconds.
        
        Returns:
            Optional[float]: Flight duration in seconds, or None if unknown
        """
        duration = self.get_duration()
        if not duration:
            return None
            
        return duration.total_seconds()

    def get_formatted_duration(self) -> str:
        """
        Get a formatted string of the flight duration.
        
        Returns:
            str: Formatted duration (HH:MM:SS), or empty string if unknown
        """
        duration_seconds = self.get_duration_seconds()
        if duration_seconds is None:
            return ""
            
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the flight data to a dictionary.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the flight data
        """
        # Ensure statistics are up to date
        if not self._statistics_calculated and self.positions:
            self.calculate_statistics()
            
        # Basic metadata
        result = {
            'filename': self.filename,
            'pilot_name': self.pilot_name,
            'glider_type': self.glider_type,
            'glider_id': self.glider_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.get_duration_seconds(),
            'duration_formatted': self.get_formatted_duration(),
            'position_count': len(self.positions),
            'attitude_count': len(self.attitudes)
        }
        
        # Statistics
        result.update({
            'statistics': {
                'max_altitude_meters': self.max_altitude_meters,
                'max_altitude_feet': self.max_altitude_meters * METERS_TO_FEET,
                'min_altitude_meters': self.min_altitude_meters,
                'min_altitude_feet': self.min_altitude_meters * METERS_TO_FEET,
                'max_speed_mps': self.max_speed_mps,
                'max_speed_kts': self.max_speed_mps * MPS_TO_KTS,
                'avg_speed_mps': self.avg_speed_mps,
                'avg_speed_kts': self.avg_speed_mps * MPS_TO_KTS,
                'distance_km': self.distance_km
            }
        })
        
        # If we have derived metadata, include it
        if self._metadata:
            result['metadata'] = self._metadata
            
        return result

    def save_metadata_file(self) -> Optional[str]:
        """
        Save flight metadata to a JSON file alongside the IGC file.
        
        Returns:
            Optional[str]: Path to the metadata file, or None if error
        """
        if not self.filename:
            logger.warning("Cannot save metadata: No filename specified")
            return None
            
        try:
            # Generate metadata filename by replacing .igc with .json
            metadata_filename = os.path.splitext(self.filename)[0] + ".json"
            
            # Convert to dictionary
            data = self.to_dict()
            
            # Write to file
            with open(metadata_filename, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved flight metadata to {metadata_filename}")
            return metadata_filename
            
        except Exception as e:
            logger.error(f"Error saving flight metadata: {e}")
            return None

    @staticmethod
    def load_from_metadata_file(metadata_filename: str) -> Optional['FlightData']:
        """
        Load flight data from a metadata JSON file.
        
        Args:
            metadata_filename: Path to the metadata JSON file
            
        Returns:
            Optional[FlightData]: Loaded flight data, or None if error
        """
        try:
            if not os.path.exists(metadata_filename):
                logger.error(f"Metadata file not found: {metadata_filename}")
                return None
                
            # Read JSON file
            with open(metadata_filename, 'r') as f:
                data = json.load(f)
                
            # Create flight data object
            flight = FlightData()
            
            # Set basic properties
            flight.filename = data.get('filename')
            flight.pilot_name = data.get('pilot_name', "")
            flight.glider_type = data.get('glider_type', "")
            flight.glider_id = data.get('glider_id', "")
            
            # Parse timestamps
            if 'start_time' in data and data['start_time']:
                try:
                    flight.start_time = datetime.datetime.fromisoformat(data['start_time'])
                except ValueError:
                    logger.warning(f"Invalid start_time format in metadata: {data['start_time']}")
                    
            if 'end_time' in data and data['end_time']:
                try:
                    flight.end_time = datetime.datetime.fromisoformat(data['end_time'])
                except ValueError:
                    logger.warning(f"Invalid end_time format in metadata: {data['end_time']}")
            
            # Set statistics
            if 'statistics' in data:
                stats = data['statistics']
                flight.max_altitude_meters = stats.get('max_altitude_meters', 0.0)
                flight.min_altitude_meters = stats.get('min_altitude_meters', 0.0)
                flight.max_speed_mps = stats.get('max_speed_mps', 0.0)
                flight.avg_speed_mps = stats.get('avg_speed_mps', 0.0)
                flight.distance_km = stats.get('distance_km', 0.0)
                
            # Set derived metadata
            if 'metadata' in data:
                flight._metadata = data['metadata']
                
            # Mark statistics as calculated
            flight._statistics_calculated = True
            
            return flight
            
        except Exception as e:
            logger.error(f"Error loading flight metadata from {metadata_filename}: {e}")
            return None


class FlightManager:
    """
    Manages multiple flights and provides search/filtering capabilities.
    """

    def __init__(self, igc_directory: Optional[str] = None):
        """
        Initialize the flight manager.
        
        Args:
            igc_directory: Optional directory containing IGC files
        """
        self.igc_directory = igc_directory or get_igc_directory()
        self.flights: List[FlightData] = []
        
    def load_flights(self) -> int:
        """
        Load all flights from the IGC directory.
        
        Returns:
            int: Number of flights loaded
        """
        try:
            # Check if directory exists
            if not os.path.exists(self.igc_directory):
                logger.warning(f"IGC directory does not exist: {self.igc_directory}")
                return 0
            
            # Find all IGC files
            igc_files = []
            for root, _, files in os.walk(self.igc_directory):
                for file in files:
                    if file.lower().endswith('.igc'):
                        igc_files.append(os.path.join(root, file))
            
            # Reset flights list
            self.flights = []
            
            # Load each flight
            for igc_file in igc_files:
                # Check for metadata file first
                metadata_file = os.path.splitext(igc_file)[0] + ".json"
                
                if os.path.exists(metadata_file):
                    # Load from metadata file
                    flight = FlightData.load_from_metadata_file(metadata_file)
                    if flight:
                        self.flights.append(flight)
                else:
                    # Load directly from IGC file
                    flight = FlightData(igc_file)
                    self.flights.append(flight)
            
            # Sort by start time (newest first)
            self.flights.sort(
                key=lambda f: f.start_time if f.start_time else datetime.datetime.min,
                reverse=True
            )
            
            logger.info(f"Loaded {len(self.flights)} flights from {self.igc_directory}")
            return len(self.flights)
            
        except Exception as e:
            logger.error(f"Error loading flights: {e}")
            return 0
    
    def get_flight_by_filename(self, filename: str) -> Optional[FlightData]:
        """
        Get a flight by its filename.
        
        Args:
            filename: Path to the IGC file
            
        Returns:
            Optional[FlightData]: Flight data if found, None otherwise
        """
        for flight in self.flights:
            if flight.filename == filename:
                return flight
        return None
    
    def search_flights(self, 
                      start_date: Optional[datetime.date] = None,
                      end_date: Optional[datetime.date] = None,
                      pilot_name: Optional[str] = None,
                      glider_type: Optional[str] = None,
                      min_duration_seconds: Optional[float] = None) -> List[FlightData]:
        """
        Search flights based on criteria.
        
        Args:
            start_date: Optional minimum flight date
            end_date: Optional maximum flight date
            pilot_name: Optional pilot name filter (case-insensitive substring)
            glider_type: Optional glider type filter (case-insensitive substring)
            min_duration_seconds: Optional minimum flight duration in seconds
            
        Returns:
            List[FlightData]: List of matching flights
        """
        result = []
        
        for flight in self.flights:
            # Apply date filters
            if start_date and flight.start_time and flight.start_time.date() < start_date:
                continue
                
            if end_date and flight.start_time and flight.start_time.date() > end_date:
                continue
            
            # Apply pilot name filter
            if pilot_name and not pilot_name.lower() in flight.pilot_name.lower():
                continue
                
            # Apply glider type filter
            if glider_type and not glider_type.lower() in flight.glider_type.lower():
                continue
                
            # Apply duration filter
            if min_duration_seconds:
                duration = flight.get_duration_seconds()
                if not duration or duration < min_duration_seconds:
                    continue
            
            # All filters passed, add to result
            result.append(flight)
            
        return result


# Create a global flight manager
flight_manager = FlightManager()
