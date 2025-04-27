"""
Aerofly FS4 IGC Recorder
Connects Aerofly FS4 Flight Simulator and generates IGC flight logs.

Features:
- Recording flight data from Aerofly FS4
- Generating IGC files
- Providing a GUI interface for easy operation
"""

__version__ = '1.0.0'
APP_NAME = 'Aerofly FS4 IGC Recorder'

from . import config
from . import data
from . import utils
from .config.constants import APP_NAME, APP_VERSION, APP_AUTHOR, APP_LICENSE

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
