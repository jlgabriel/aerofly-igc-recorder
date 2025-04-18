"""
Core package for Aerofly FS4 IGC Recorder.
Contains the main business logic for the application.
"""

from .recorder import FlightRecorder, create_flight_recorder
from .bridge import AeroflyBridge, create_bridge, run_bridge
from .flight import FlightData, FlightManager, flight_manager

__all__ = [
    'FlightRecorder',
    'create_flight_recorder',
    'AeroflyBridge',
    'create_bridge',
    'run_bridge',
    'FlightData',
    'FlightManager',
    'flight_manager'
]