"""
Tests for data models.
"""

import pytest
import datetime
from app.data.models import (
    XGPSData, XATTData, UnknownData, DataType
)


class TestXGPSData:
    """Test cases for XGPSData model."""

    def test_create_valid_xgps_data(self):
        """Test creating valid XGPS data."""
        data = XGPSData(
            sim_name="Aerofly FS 4",
            longitude=-122.345678,
            latitude=37.654321,
            alt_msl_meters=500.0,
            track_deg=180.0,
            ground_speed_mps=50.0
        )

        assert data.sim_name == "Aerofly FS 4"
        assert data.longitude == -122.345678
        assert data.latitude == 37.654321
        assert data.alt_msl_meters == 500.0
        assert data.track_deg == 180.0
        assert data.ground_speed_mps == 50.0
        assert data.data_type == DataType.GPS

    def test_xgps_with_timestamp(self):
        """Test XGPS data with explicit timestamp."""
        now = datetime.datetime.now(datetime.timezone.utc)
        data = XGPSData(
            sim_name="Test",
            longitude=0.0,
            latitude=0.0,
            alt_msl_meters=0.0,
            track_deg=0.0,
            ground_speed_mps=0.0,
            timestamp=now
        )

        assert data.timestamp == now

    def test_xgps_validation_latitude_range(self):
        """Test latitude validation (should be -90 to 90)."""
        # Valid latitudes
        XGPSData(sim_name="Test", longitude=0.0, latitude=-90.0,
                 alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)
        XGPSData(sim_name="Test", longitude=0.0, latitude=90.0,
                 alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)
        XGPSData(sim_name="Test", longitude=0.0, latitude=0.0,
                 alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)

        # Invalid latitudes should raise ValueError
        with pytest.raises(ValueError):
            XGPSData(sim_name="Test", longitude=0.0, latitude=91.0,
                     alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)

        with pytest.raises(ValueError):
            XGPSData(sim_name="Test", longitude=0.0, latitude=-91.0,
                     alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)

    def test_xgps_validation_longitude_range(self):
        """Test longitude validation (should be -180 to 180)."""
        # Valid longitudes
        XGPSData(sim_name="Test", longitude=-180.0, latitude=0.0,
                 alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)
        XGPSData(sim_name="Test", longitude=180.0, latitude=0.0,
                 alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)

        # Invalid longitudes should raise ValueError
        with pytest.raises(ValueError):
            XGPSData(sim_name="Test", longitude=181.0, latitude=0.0,
                     alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)

        with pytest.raises(ValueError):
            XGPSData(sim_name="Test", longitude=-181.0, latitude=0.0,
                     alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)

    def test_xgps_validation_track_range(self):
        """Test track validation (should be 0 to 360)."""
        # Valid tracks
        XGPSData(sim_name="Test", longitude=0.0, latitude=0.0,
                 alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)
        XGPSData(sim_name="Test", longitude=0.0, latitude=0.0,
                 alt_msl_meters=0.0, track_deg=360.0, ground_speed_mps=0.0)

        # Invalid tracks should raise ValueError
        with pytest.raises(ValueError):
            XGPSData(sim_name="Test", longitude=0.0, latitude=0.0,
                     alt_msl_meters=0.0, track_deg=-1.0, ground_speed_mps=0.0)

        with pytest.raises(ValueError):
            XGPSData(sim_name="Test", longitude=0.0, latitude=0.0,
                     alt_msl_meters=0.0, track_deg=361.0, ground_speed_mps=0.0)

    def test_xgps_validation_speed(self):
        """Test speed validation (should be non-negative)."""
        # Valid speeds
        XGPSData(sim_name="Test", longitude=0.0, latitude=0.0,
                 alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=0.0)
        XGPSData(sim_name="Test", longitude=0.0, latitude=0.0,
                 alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=100.0)

        # Negative speed should raise ValueError
        with pytest.raises(ValueError):
            XGPSData(sim_name="Test", longitude=0.0, latitude=0.0,
                     alt_msl_meters=0.0, track_deg=0.0, ground_speed_mps=-1.0)


class TestXATTData:
    """Test cases for XATTData model."""

    def test_create_valid_xatt_data(self):
        """Test creating valid XATT data."""
        data = XATTData(
            sim_name="Aerofly FS 4",
            heading_deg=180.0,
            pitch_deg=15.0,
            roll_deg=-5.0
        )

        assert data.sim_name == "Aerofly FS 4"
        assert data.heading_deg == 180.0
        assert data.pitch_deg == 15.0
        assert data.roll_deg == -5.0
        assert data.data_type == DataType.ATTITUDE

    def test_xatt_validation_heading_range(self):
        """Test heading validation (should be 0 to 360)."""
        # Valid headings
        XATTData(sim_name="Test", heading_deg=0.0, pitch_deg=0.0, roll_deg=0.0)
        XATTData(sim_name="Test", heading_deg=360.0, pitch_deg=0.0, roll_deg=0.0)

        # Invalid headings should raise ValueError
        with pytest.raises(ValueError):
            XATTData(sim_name="Test", heading_deg=-1.0, pitch_deg=0.0, roll_deg=0.0)

        with pytest.raises(ValueError):
            XATTData(sim_name="Test", heading_deg=361.0, pitch_deg=0.0, roll_deg=0.0)

    def test_xatt_validation_pitch_range(self):
        """Test pitch validation (should be -90 to 90)."""
        # Valid pitches
        XATTData(sim_name="Test", heading_deg=0.0, pitch_deg=-90.0, roll_deg=0.0)
        XATTData(sim_name="Test", heading_deg=0.0, pitch_deg=90.0, roll_deg=0.0)

        # Invalid pitches should raise ValueError
        with pytest.raises(ValueError):
            XATTData(sim_name="Test", heading_deg=0.0, pitch_deg=-91.0, roll_deg=0.0)

        with pytest.raises(ValueError):
            XATTData(sim_name="Test", heading_deg=0.0, pitch_deg=91.0, roll_deg=0.0)

    def test_xatt_validation_roll_range(self):
        """Test roll validation (should be -180 to 180)."""
        # Valid rolls
        XATTData(sim_name="Test", heading_deg=0.0, pitch_deg=0.0, roll_deg=-180.0)
        XATTData(sim_name="Test", heading_deg=0.0, pitch_deg=0.0, roll_deg=180.0)

        # Invalid rolls should raise ValueError
        with pytest.raises(ValueError):
            XATTData(sim_name="Test", heading_deg=0.0, pitch_deg=0.0, roll_deg=-181.0)

        with pytest.raises(ValueError):
            XATTData(sim_name="Test", heading_deg=0.0, pitch_deg=0.0, roll_deg=181.0)


class TestUnknownData:
    """Test cases for UnknownData model."""

    def test_create_unknown_data(self):
        """Test creating UnknownData."""
        data = UnknownData(raw_data="INVALID_LINE")

        assert data.raw_data == "INVALID_LINE"
        assert data.data_type == DataType.UNKNOWN

    def test_unknown_data_with_empty_string(self):
        """Test UnknownData with empty string."""
        data = UnknownData(raw_data="")

        assert data.raw_data == ""
        assert data.data_type == DataType.UNKNOWN


class TestDataType:
    """Test cases for DataType enum."""

    def test_data_type_values(self):
        """Test DataType enum values."""
        assert DataType.GPS.value == "XGPS"
        assert DataType.ATTITUDE.value == "XATT"
        assert DataType.UNKNOWN.value == "UNKNOWN"

    def test_data_type_membership(self):
        """Test DataType enum membership."""
        assert DataType.GPS in DataType
        assert DataType.ATTITUDE in DataType
        assert DataType.UNKNOWN in DataType
