"""
UI package for Aerofly FS4 IGC Recorder.
Contains GUI and CLI interfaces for the application.
"""

from .gui import GUI, create_gui
from .cli import CLI, create_cli

__all__ = [
    'GUI',
    'create_gui',
    'CLI',
    'create_cli'
]