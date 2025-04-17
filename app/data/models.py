"""
Data models for Aerofly FS4 IGC Recorder.
Contains classes representing different types of flight data.
"""

from dataclasses import dataclass
from typing import Optional, Union, List, Dict, Any
import datetime
from enum import Enum


class DataType(Enum):
    """Enum for different types of ForeFlight data"""
    GPS = "XGPS"
    ATTITUDE = "XATT"
    UNKNOWN = "UNKNOWN"


@dataclass
class XGPSData:
    """
    Represents ForeFlight XGPS position data.
    Format: XGPS<sim_name>,<longitude>,<latitude>,<altitude_msl_meters>,<track_true_north>,<groundspeed_m/s>
    """
    sim_name: str
    longitude: float
    latitude: float
    alt_msl_meters: float
    track_deg: float
    ground_speed_mps: float
    timestamp: Optional[datetime.datetime] = None

    def __post_init__(self):
        """Validate data after initialization"""
        if not isinstance(self.sim_name, str):
            raise TypeError("sim_name must be a string")
        if not isinstance(self.longitude, (int, float)):
            raise TypeError("longitude must be a number")
        if not isinstance(self.latitude, (int, float)):
            raise TypeError("latitude must be a number")
        if not isinstance(self.alt_msl_meters, (int, float)):
            raise TypeError("alt_msl_meters must be a number")
        if not isinstance(self.track_deg, (int, float)):
            raise TypeError("track_deg must be a number")
        if not isinstance(self.ground_speed_mps, (int, float)):
            raise TypeError("ground_speed_mps must be a number")

        # Validate ranges
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not 0 <= self.track_deg <= 360:
            raise ValueError("track_deg must be between 0 and 360")
        if self.ground_speed_mps < 0:
            raise ValueError("ground_speed_mps cannot be negative")

        # Set timestamp if not provided
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc)

    @property
    def data_type(self) -> DataType:
        """Return the data type of this object"""
        return DataType.GPS

    def to_dict(self) -> Dict[str, Any]:
        """Convert the object to a dictionary"""
        return {
            "type": self.data_type.value,
            "sim_name": self.sim_name,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "alt_msl_meters": self.alt_msl_meters,
            "track_deg": self.track_deg,
            "ground_speed_mps": self.ground_speed_mps,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class XATTData:
    """
    Represents ForeFlight XATT attitude data.
    Format: XATT<sim_name>,<true_heading_deg>,<pitch_deg>,<roll_deg>
    """
    sim_name: str
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    timestamp: Optional[datetime.datetime] = None

    def __post_init__(self):
        """Validate data after initialization"""
        if not isinstance(self.sim_name, str):
            raise TypeError("sim_name must be a string")
        if not isinstance(self.heading_deg, (int, float)):
            raise TypeError("heading_deg must be a number")
        if not isinstance(self.pitch_deg, (int, float)):
            raise TypeError("pitch_deg must be a number")
        if not isinstance(self.roll_deg, (int, float)):
            raise TypeError("roll_deg must be a number")

        # Validate ranges
        if not 0 <= self.heading_deg <= 360:
            raise ValueError("heading_deg must be between 0 and 360")
        if not -90 <= self.pitch_deg <= 90:
            raise ValueError("pitch_deg must be between -90 and 90")
        if not -180 <= self.roll_deg <= 180:
            raise ValueError("roll_deg must be between -180 and 180")

        # Set timestamp if not provided
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc)

    @property
    def data_type(self) -> DataType:
        """Return the data type of this object"""
        return DataType.ATTITUDE

    def to_dict(self) -> Dict[str, Any]:
        """Convert the object to a dictionary"""
        return {
            "type": self.data_type.value,
            "sim_name": self.sim_name,
            "heading_deg": self.heading_deg,
            "pitch_deg": self.pitch_deg,
            "roll_deg": self.roll_deg,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class UnknownData:
    """
    Represents unparsed or unrecognized data.
    """
    raw_line: str
    timestamp: Optional[datetime.datetime] = None

    def __post_init__(self):
        """Set timestamp if not provided"""
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc)

    @property
    def data_type(self) -> DataType:
        """Return the data type of this object"""
        return DataType.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """Convert the object to a dictionary"""
        return {
            "type": self.data_type.value,
            "raw_line": self.raw_line,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


# Type hint for a generic ForeFlight data object
ForeFlightData = Union[XGPSData, XATTData, UnknownData]
