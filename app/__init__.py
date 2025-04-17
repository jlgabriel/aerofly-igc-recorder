"""
Aerofly FS4 IGC Recorder
A tool to connect Aerofly FS4 Flight Simulator and generate IGC flight logs.

This package contains modules for:
- Receiving UDP data from Aerofly FS4
- Parsing ForeFlight-compatible data formats
- Recording flight data to IGC files
- Providing both GUI and CLI interfaces
"""

from . import config
from . import data
from . import utils
from .config.constants import APP_NAME, APP_VERSION, APP_AUTHOR, APP_LICENSE

__version__ = APP_VERSION
__author__ = APP_AUTHOR
__license__ = APP_LICENSE

# Initialize logging when the package is imported
import logging
import sys

# Configure root logger
root_logger = logging.getLogger("aerofly_igc_recorder")
root_logger.setLevel(logging.INFO)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add handler to logger
root_logger.addHandler(console_handler)

# Log initialization
root_logger.info(f"Initializing {APP_NAME} v{APP_VERSION}")
