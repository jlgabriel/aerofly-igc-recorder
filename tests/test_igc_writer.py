"""
Tests for IGC writer module.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
import datetime
from app.io.igc import IGCWriter
from app.data.models import XGPSData, XATTData


class TestIGCWriter:
    """Test cases for IGCWriter class."""

    @pytest.fixture
    def temp_igc_dir(self):
        """Create a temporary directory for IGC files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def writer_instance(self, temp_igc_dir):
        """Create a fresh IGCWriter instance with temp directory."""
        writer = IGCWriter(igc_directory=str(temp_igc_dir))
        return writer

    @pytest.mark.asyncio
    async def test_start_recording(self, writer_instance):
        """Test starting a recording session."""
        filename = await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST123"
        )

        assert filename is not None
        assert isinstance(filename, str)
        assert filename.endswith('.igc')
        assert writer_instance.recording is True
        assert writer_instance.current_file is not None

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_start_recording_creates_file(self, writer_instance, temp_igc_dir):
        """Test that start_recording creates an IGC file."""
        filename = await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST"
        )

        file_path = Path(filename)
        assert file_path.exists()
        assert file_path.parent == temp_igc_dir

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_stop_recording(self, writer_instance):
        """Test stopping a recording session."""
        # Start recording first
        await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST"
        )

        # Stop recording
        filename = await writer_instance.stop_recording()

        assert filename is not None
        assert writer_instance.recording is False
        assert writer_instance.current_file is None

    @pytest.mark.asyncio
    async def test_stop_without_start(self, writer_instance):
        """Test stopping recording when not started."""
        filename = await writer_instance.stop_recording()

        # Should return None or handle gracefully
        assert filename is None

    @pytest.mark.asyncio
    async def test_add_position_while_recording(self, writer_instance):
        """Test adding position data while recording."""
        # Start recording
        await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST"
        )

        # Create position data
        gps_data = XGPSData(
            sim_name="Test",
            longitude=-122.0,
            latitude=37.0,
            alt_msl_meters=500.0,
            track_deg=180.0,
            ground_speed_mps=25.0
        )

        # Add position
        await writer_instance.add_position(gps_data)

        # Check recording status
        status = writer_instance.get_recording_status()
        assert status['recording'] is True
        assert status['fix_count'] >= 1

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_add_position_without_recording(self, writer_instance):
        """Test adding position when not recording."""
        gps_data = XGPSData(
            sim_name="Test",
            longitude=-122.0,
            latitude=37.0,
            alt_msl_meters=500.0,
            track_deg=180.0,
            ground_speed_mps=25.0
        )

        # Should handle gracefully (not crash)
        await writer_instance.add_position(gps_data)

        status = writer_instance.get_recording_status()
        assert status['recording'] is False

    @pytest.mark.asyncio
    async def test_add_multiple_positions(self, writer_instance):
        """Test adding multiple position fixes."""
        await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST"
        )

        # Add multiple positions
        for i in range(5):
            gps_data = XGPSData(
                sim_name="Test",
                longitude=-122.0 + i * 0.01,
                latitude=37.0 + i * 0.01,
                alt_msl_meters=500.0 + i * 10,
                track_deg=180.0,
                ground_speed_mps=25.0
            )
            await writer_instance.add_position(gps_data)
            await asyncio.sleep(0.01)  # Small delay

        status = writer_instance.get_recording_status()
        assert status['fix_count'] >= 5

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_add_position_with_attitude(self, writer_instance):
        """Test adding position with attitude data."""
        await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST"
        )

        gps_data = XGPSData(
            sim_name="Test",
            longitude=-122.0,
            latitude=37.0,
            alt_msl_meters=500.0,
            track_deg=180.0,
            ground_speed_mps=25.0
        )

        att_data = XATTData(
            sim_name="Test",
            heading_deg=180.0,
            pitch_deg=10.0,
            roll_deg=-5.0
        )

        # Add position with attitude
        await writer_instance.add_position(gps_data, att_data)

        status = writer_instance.get_recording_status()
        assert status['fix_count'] >= 1

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_recording_status_not_recording(self, writer_instance):
        """Test getting status when not recording."""
        status = writer_instance.get_recording_status()

        assert isinstance(status, dict)
        assert status['recording'] is False
        assert status['fix_count'] == 0
        assert status['filename'] is None

    @pytest.mark.asyncio
    async def test_recording_status_while_recording(self, writer_instance):
        """Test getting status while recording."""
        filename = await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST"
        )

        status = writer_instance.get_recording_status()

        assert status['recording'] is True
        assert status['filename'] == filename
        assert 'fix_count' in status
        assert 'start_time' in status
        assert 'duration' in status

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_filename_format(self, writer_instance):
        """Test that generated filename follows expected format."""
        filename = await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST"
        )

        # Filename should contain date and .igc extension
        assert filename.endswith('.igc')
        # Should be a valid path
        assert Path(filename).is_absolute()

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_file_content_has_headers(self, writer_instance, temp_igc_dir):
        """Test that IGC file contains required headers."""
        filename = await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST123"
        )

        # Add at least one position
        gps_data = XGPSData(
            sim_name="Test",
            longitude=-122.0,
            latitude=37.0,
            alt_msl_meters=500.0,
            track_deg=180.0,
            ground_speed_mps=25.0
        )
        await writer_instance.add_position(gps_data)

        # Stop recording
        await writer_instance.stop_recording()

        # Read file and check for IGC headers
        with open(filename, 'r') as f:
            content = f.read()

        # Check for required IGC header records
        assert 'A' in content  # FR manufacturer and ID
        assert 'HFDTE' in content  # Date header
        assert 'HFPLT' in content or 'Test Pilot' in content  # Pilot
        assert 'HFGTY' in content or 'Test Glider' in content  # Glider type
        assert 'B' in content  # Fix record

    @pytest.mark.asyncio
    async def test_concurrent_recording_prevention(self, writer_instance):
        """Test that starting a new recording while one is active fails gracefully."""
        # Start first recording
        filename1 = await writer_instance.start_recording(
            pilot_name="Pilot 1",
            glider_type="Glider 1",
            glider_id="TEST1"
        )

        assert filename1 is not None

        # Try to start second recording
        filename2 = await writer_instance.start_recording(
            pilot_name="Pilot 2",
            glider_type="Glider 2",
            glider_id="TEST2"
        )

        # Should either return None or same filename
        assert filename2 is None or filename2 == filename1

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_recording_duration(self, writer_instance):
        """Test that recording duration is tracked."""
        await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="Test Glider",
            glider_id="TEST"
        )

        # Wait a bit
        await asyncio.sleep(0.1)

        status = writer_instance.get_recording_status()

        # Duration should be > 0
        assert status['duration'] > 0

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_glider_info_in_recording(self, writer_instance):
        """Test recording with additional glider info."""
        glider_info = {
            'manufacturer': 'Schleicher',
            'model': 'ASK 21',
            'competition_id': 'AB',
            'competition_class': 'Club'
        }

        filename = await writer_instance.start_recording(
            pilot_name="Test Pilot",
            glider_type="ASK 21",
            glider_id="D-1234",
            glider_info=glider_info
        )

        assert filename is not None

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_empty_pilot_name(self, writer_instance):
        """Test recording with empty pilot name."""
        filename = await writer_instance.start_recording(
            pilot_name="",
            glider_type="Test Glider",
            glider_id="TEST"
        )

        # Should still create a file
        assert filename is not None

        # Clean up
        await writer_instance.stop_recording()

    @pytest.mark.asyncio
    async def test_special_characters_in_names(self, writer_instance):
        """Test recording with special characters in names."""
        filename = await writer_instance.start_recording(
            pilot_name="Test-Pilot_123",
            glider_type="Glider (Test)",
            glider_id="D-ABCD"
        )

        # Should handle special characters
        assert filename is not None
        assert Path(filename).exists()

        # Clean up
        await writer_instance.stop_recording()
