"""
Data package for Aerofly FS4 IGC Recorder.
Contains data models and parsers for ForeFlight-compatible data.
"""

from .models import XGPSData, XATTData, UnknownData, ForeFlightData, DataType
from .parser import ForeFlightParser, parser

__all__ = [
    'XGPSData',
    'XATTData',
    'UnknownData',
    'ForeFlightData',
    'DataType',
    'ForeFlightParser',
    'parser'
]