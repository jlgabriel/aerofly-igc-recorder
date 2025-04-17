"""
Constants for Aerofly FS4 IGC Recorder.
These are fixed values that don't change during application execution.
"""

# Unit conversion factors
METERS_TO_FEET = 3.28084
MPS_TO_KTS = 1.94384  # Meters per second to knots
MPS_TO_FPM = 196.85   # Meters per second to feet per minute

# Network constants
DEFAULT_UDP_PORT = 49002
DEFAULT_BUFFER_SIZE = 1024
DEFAULT_ENCODING = 'utf-8'

# IGC file related constants
IGC_EXTENSION = '.igc'
IGC_MANUFACTURER_CODE = 'XAF'  # Arbitrary code for Aerofly
IGC_LOGGER_ID = 'SIM'  # Default logger ID for simulator

# ForeFlight message prefixes
XGPS_PREFIX = 'XGPS'
XATT_PREFIX = 'XATT'

# Application information
APP_NAME = "Aerofly FS4 IGC Recorder"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Juan Luis Gabriel"
APP_LICENSE = "MIT License"
APP_WEBSITE = "https://github.com/jlgabriel/aerofly-igc-recorder"
APP_DESCRIPTION = "Connect Aerofly FS4 Flight Simulator and generate IGC flight logs"

# GUI Constants
DEFAULT_WINDOW_WIDTH = 600
DEFAULT_WINDOW_HEIGHT = 580
GUI_REFRESH_RATE_MS = 100  # GUI refresh rate in milliseconds
GUI_FONT_FAMILY = "Consolas"
GUI_FONT_SIZE = 9

# Time constants
CONNECTION_TIMEOUT_SECONDS = 5.0   # Time threshold to consider connection lost
RECORDING_INTERVAL_SECONDS = 1.0   # Default interval between IGC position records
