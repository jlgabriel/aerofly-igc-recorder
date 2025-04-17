"""
Parser for ForeFlight-compatible data formats used in Aerofly FS4.
"""

import logging
from typing import Union, Optional
import datetime
from .models import XGPSData, XATTData, UnknownData, ForeFlightData
from ..config.constants import XGPS_PREFIX, XATT_PREFIX

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.parser")


class ForeFlightParser:
    """
    Parses strings in ForeFlight's XGPS / XATT formats,
    returning typed objects: XGPSData, XATTData, or UnknownData.
    """

    @staticmethod
    def parse_line(line: str, timestamp: Optional[datetime.datetime] = None) -> ForeFlightData:
        """
        Identify the data type (XGPS, XATT) and parse accordingly.
        
        Args:
            line: The raw data line to parse
            timestamp: Optional timestamp to associate with the parsed data
            
        Returns:
            Union[XGPSData, XATTData, UnknownData]: The parsed data object
        """
        if not line:
            return UnknownData(raw_line="", timestamp=timestamp)
            
        line = line.strip()
        
        try:
            if line.startswith(XGPS_PREFIX):
                return ForeFlightParser._parse_xgps(line, timestamp)
            elif line.startswith(XATT_PREFIX):
                return ForeFlightParser._parse_xatt(line, timestamp)
            else:
                return UnknownData(raw_line=line, timestamp=timestamp)
        except Exception as e:
            logger.warning(f"Error parsing line: {line}. Error: {e}")
            return UnknownData(raw_line=line, timestamp=timestamp)

    @staticmethod
    def _parse_xgps(line: str, timestamp: Optional[datetime.datetime] = None) -> Union[XGPSData, UnknownData]:
        """
        Parse an XGPS data line.
        
        Example XGPS line:
        XGPSMySim,-80.11,34.55,1200.1,359.05,55.6
        => XGPS<sim_name>,<longitude>,<latitude>,<alt_msl_meters>,<track_deg_true>,<groundspeed_m/s>
        
        Args:
            line: The raw XGPS line to parse
            timestamp: Optional timestamp to associate with the parsed data
            
        Returns:
            Union[XGPSData, UnknownData]: The parsed data object
        """
        try:
            raw = line[len(XGPS_PREFIX):]  # remove 'XGPS'
            parts = raw.split(",")
            
            if len(parts) < 6:
                logger.warning(f"Invalid XGPS data format (not enough parts): {line}")
                return UnknownData(raw_line=line, timestamp=timestamp)
                
            sim_name = parts[0].strip()
            
            # Parse numeric values, handling potential errors
            try:
                longitude = float(parts[1])
                latitude = float(parts[2])
                alt_msl_meters = float(parts[3])
                track_deg = float(parts[4])
                ground_speed_mps = float(parts[5])
            except ValueError as e:
                logger.warning(f"Invalid numeric value in XGPS data: {line}. Error: {e}")
                return UnknownData(raw_line=line, timestamp=timestamp)

            # Create and return the XGPSData object
            try:
                return XGPSData(
                    sim_name=sim_name,
                    longitude=longitude,
                    latitude=latitude,
                    alt_msl_meters=alt_msl_meters,
                    track_deg=track_deg,
                    ground_speed_mps=ground_speed_mps,
                    timestamp=timestamp
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Error creating XGPSData: {e}")
                return UnknownData(raw_line=line, timestamp=timestamp)
                
        except Exception as e:
            logger.warning(f"Unexpected error parsing XGPS data: {e}")
            return UnknownData(raw_line=line, timestamp=timestamp)

    @staticmethod
    def _parse_xatt(line: str, timestamp: Optional[datetime.datetime] = None) -> Union[XATTData, UnknownData]:
        """
        Parse an XATT data line.
        
        Example XATT line:
        XATTMySim,180.2,0.1,0.2
        => XATT<sim_name>,<true_heading_deg>,<pitch_deg>,<roll_deg>
        
        Args:
            line: The raw XATT line to parse
            timestamp: Optional timestamp to associate with the parsed data
            
        Returns:
            Union[XATTData, UnknownData]: The parsed data object
        """
        try:
            raw = line[len(XATT_PREFIX):]  # remove 'XATT'
            parts = raw.split(",")
            
            if len(parts) < 4:
                logger.warning(f"Invalid XATT data format (not enough parts): {line}")
                return UnknownData(raw_line=line, timestamp=timestamp)
                
            sim_name = parts[0].strip()
            
            # Parse numeric values, handling potential errors
            try:
                heading_deg = float(parts[1])
                pitch_deg = float(parts[2])
                roll_deg = float(parts[3])
            except ValueError as e:
                logger.warning(f"Invalid numeric value in XATT data: {line}. Error: {e}")
                return UnknownData(raw_line=line, timestamp=timestamp)

            # Create and return the XATTData object
            try:
                return XATTData(
                    sim_name=sim_name,
                    heading_deg=heading_deg,
                    pitch_deg=pitch_deg,
                    roll_deg=roll_deg,
                    timestamp=timestamp
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Error creating XATTData: {e}")
                return UnknownData(raw_line=line, timestamp=timestamp)
                
        except Exception as e:
            logger.warning(f"Unexpected error parsing XATT data: {e}")
            return UnknownData(raw_line=line, timestamp=timestamp)


# Create a singleton instance of the parser
parser = ForeFlightParser()
