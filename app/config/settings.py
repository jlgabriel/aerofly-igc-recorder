"""
Settings for Aerofly FS4 IGC Recorder.
These are configurable parameters that can be changed by the user.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .constants import DEFAULT_UDP_PORT

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("aerofly_igc_recorder.settings")


class Settings:
    """
    Application settings that can be loaded from and saved to a configuration file.
    Uses a singleton pattern to ensure only one settings instance exists.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Settings, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        # Default settings
        self._settings = {
            # Network settings
            "udp_port": DEFAULT_UDP_PORT,
            
            # File paths
            "igc_directory": self._get_default_igc_dir(),
            
            # Recording settings
            "default_pilot_name": "Simulator Pilot",
            "default_glider_type": "Aerofly FS4",
            "default_glider_id": "SIM",
            "recording_interval": 1.0,  # seconds
            
            # UI settings
            "window_width": 600,
            "window_height": 580,
            "theme": "system",  # Can be "light", "dark", or "system"
            "show_tooltips": True,
            "log_level": "INFO",
        }
        
        # Load settings from file if it exists
        self._config_dir = self._get_config_dir()
        self._config_file = os.path.join(self._config_dir, "settings.json")
        self._load_settings()
        
        self._initialized = True

    @staticmethod
    def _get_config_dir() -> str:
        """Get the configuration directory for the application"""
        # Use platform-specific config locations
        if os.name == 'nt':  # Windows
            config_dir = os.path.join(os.environ.get('APPDATA', ''), 'AeroflyIGCRecorder')
        else:  # Linux/Mac
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, '.config', 'aerofly-igc-recorder')
        
        # Create directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    @staticmethod
    def _get_default_igc_dir() -> str:
        """Get the default directory for IGC files"""
        documents_dir = os.path.join(os.path.expanduser("~"), "Documents")
        igc_dir = os.path.join(documents_dir, "AeroflyIGC")
        os.makedirs(igc_dir, exist_ok=True)
        return igc_dir

    def _load_settings(self) -> None:
        """Load settings from the configuration file"""
        try:
            if os.path.exists(self._config_file):
                with open(self._config_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Update default settings with loaded ones
                    self._settings.update(loaded_settings)
                logger.info(f"Settings loaded from {self._config_file}")
            else:
                logger.info("No settings file found, using defaults")
                self.save_settings()  # Create default settings file
        except Exception as e:
            logger.error(f"Error loading settings: {e}")

    def save_settings(self) -> bool:
        """Save current settings to the configuration file"""
        try:
            with open(self._config_file, 'w') as f:
                json.dump(self._settings, f, indent=4)
            logger.info(f"Settings saved to {self._config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key"""
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value by key"""
        self._settings[key] = value

    def get_all(self) -> Dict[str, Any]:
        """Get all settings as a dictionary"""
        return self._settings.copy()

    def reset_to_defaults(self) -> None:
        """Reset all settings to their default values"""
        # Re-initialize with default settings
        self.__init__()
        # Save the defaults
        self.save_settings()
        logger.info("Settings reset to defaults")


# Create a global settings instance
settings = Settings()
