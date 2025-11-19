"""
Pytest configuration and shared fixtures.
"""

import pytest
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_dir():
    """Provide the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def app_dir(project_root_dir):
    """Provide the app directory."""
    return project_root_dir / "app"


@pytest.fixture
def sample_xgps_line():
    """Provide a sample XGPS data line for testing."""
    return "XGPSAerofly FS 4,-122.345678,37.654321,123.45,45.67,89.12"


@pytest.fixture
def sample_xatt_line():
    """Provide a sample XATT data line for testing."""
    return "XATTAerofly FS 4,180.5,15.3,-5.7"


@pytest.fixture
def sample_invalid_line():
    """Provide an invalid data line for testing."""
    return "INVALID_FORMAT"
