"""
File management utilities for Aerofly FS4 IGC Recorder.
"""

import os
import logging
import datetime
import shutil
import glob
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import sys

from ..config.settings import settings

# Configure logger
logger = logging.getLogger("aerofly_igc_recorder.io.files")


def get_igc_directory() -> str:
    """
    Get the IGC output directory, creating it if it doesn't exist.
    Uses the directory from settings.

    Returns:
        str: Path to the IGC directory
    """
    igc_dir = settings.get('igc_directory')
    os.makedirs(igc_dir, exist_ok=True)
    return igc_dir


def list_igc_files(directory: Optional[str] = None) -> List[str]:
    """
    List all IGC files in the specified directory.

    Args:
        directory: Directory to search (default: from settings)

    Returns:
        List[str]: List of IGC file paths
    """
    if directory is None:
        directory = get_igc_directory()

    try:
        # Use glob to find all .igc files
        igc_files = glob.glob(os.path.join(directory, "*.igc"))

        # Sort by modification time (newest first)
        igc_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        return igc_files
    except Exception as e:
        logger.error(f"Error listing IGC files: {e}")
        return []


def get_file_info(filepath: str) -> Dict[str, Any]:
    """
    Get information about a file.

    Args:
        filepath: Path to the file

    Returns:
        Dict[str, Any]: Dictionary with file information
    """
    try:
        if not os.path.exists(filepath):
            return {'exists': False, 'error': 'File not found'}

        stat = os.stat(filepath)

        # Get file creation and modification times
        ctime = datetime.datetime.fromtimestamp(stat.st_ctime)
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime)

        # Get file size
        size_bytes = stat.st_size

        # Format size
        if size_bytes < 1024:
            size_str = f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

        return {
            'exists': True,
            'path': filepath,
            'filename': os.path.basename(filepath),
            'directory': os.path.dirname(filepath),
            'size_bytes': size_bytes,
            'size_str': size_str,
            'created': ctime.isoformat(),
            'modified': mtime.isoformat(),
            'extension': os.path.splitext(filepath)[1].lower()
        }
    except Exception as e:
        logger.error(f"Error getting file info for {filepath}: {e}")
        return {'exists': False, 'error': str(e)}


def open_file_or_directory(path: str) -> bool:
    """
    Open a file or directory with the default system application.

    Args:
        path: Path to file or directory

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not os.path.exists(path):
            logger.error(f"Path does not exist: {path}")
            return False

        # Use appropriate method based on platform
        if sys.platform == 'win32':
            # Windows
            os.startfile(path)
        elif sys.platform == 'darwin':
            # macOS
            os.system(f'open "{path}"')
        else:
            # Linux
            os.system(f'xdg-open "{path}"')

        logger.info(f"Opened: {path}")
        return True
    except Exception as e:
        logger.error(f"Error opening {path}: {e}")
        return False


def delete_file(filepath: str) -> bool:
    """
    Delete a file.

    Args:
        filepath: Path to the file

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not os.path.exists(filepath):
            logger.warning(f"File not found: {filepath}")
            return False

        os.remove(filepath)
        logger.info(f"Deleted file: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error deleting file {filepath}: {e}")
        return False


def copy_file(source: str, destination: str, overwrite: bool = False) -> bool:
    """
    Copy a file from source to destination.

    Args:
        source: Source file path
        destination: Destination file path
        overwrite: Whether to overwrite existing destination

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not os.path.exists(source):
            logger.error(f"Source file not found: {source}")
            return False

        if os.path.exists(destination) and not overwrite:
            logger.warning(f"Destination exists and overwrite not allowed: {destination}")
            return False

        shutil.copy2(source, destination)
        logger.info(f"Copied {source} to {destination}")
        return True
    except Exception as e:
        logger.error(f"Error copying {source} to {destination}: {e}")
        return False


def rename_file(filepath: str, new_name: str) -> Optional[str]:
    """
    Rename a file.

    Args:
        filepath: Path to the file
        new_name: New filename (not path)

    Returns:
        Optional[str]: New filepath if successful, None otherwise
    """
    try:
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None

        directory = os.path.dirname(filepath)
        new_filepath = os.path.join(directory, new_name)

        if os.path.exists(new_filepath):
            logger.error(f"Destination already exists: {new_filepath}")
            return None

        os.rename(filepath, new_filepath)
        logger.info(f"Renamed {filepath} to {new_filepath}")
        return new_filepath
    except Exception as e:
        logger.error(f"Error renaming {filepath} to {new_name}: {e}")
        return None


def create_directory(path: str) -> bool:
    """
    Create a directory if it doesn't exist.

    Args:
        path: Path to create

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if os.path.exists(path):
            if os.path.isdir(path):
                logger.debug(f"Directory already exists: {path}")
                return True
            else:
                logger.error(f"Path exists but is not a directory: {path}")
                return False

        os.makedirs(path, exist_ok=True)
        logger.info(f"Created directory: {path}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return False


def get_available_filename(base_path: str, extension: str = ".igc") -> str:
    """
    Generate a unique filename that doesn't already exist.

    Args:
        base_path: Base path and prefix for the filename
        extension: File extension

    Returns:
        str: Unique filepath
    """
    counter = 1
    directory = os.path.dirname(base_path)
    basename = os.path.basename(base_path)

    # If basename already has an extension, remove it
    if '.' in basename:
        basename = os.path.splitext(basename)[0]

    # Make sure extension starts with a dot
    if not extension.startswith('.'):
        extension = '.' + extension

    # Try with original name first
    filepath = os.path.join(directory, f"{basename}{extension}")

    # If it exists, add counter until we find an available name
    while os.path.exists(filepath):
        filepath = os.path.join(directory, f"{basename}_{counter}{extension}")
        counter += 1

    return filepath