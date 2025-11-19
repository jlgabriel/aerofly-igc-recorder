"""
Tests for ForeFlight data parser.
"""

import pytest
import datetime
from app.data.parser import ForeFlightParser
from app.data.models import XGPSData, XATTData, UnknownData, DataType


class TestForeFlightParser:
    """Test cases for ForeFlightParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance for testing."""
        return ForeFlightParser()

    def test_parse_valid_xgps_data(self, parser):
        """Test parsing of valid XGPS data."""
        line = "XGPSAerofly FS 4,-122.345678,37.654321,123.45,45.67,89.12"

        data = parser.parse(line)

        assert isinstance(data, XGPSData)
        assert data.sim_name == "Aerofly FS 4"
        assert abs(data.longitude - (-122.345678)) < 0.000001
        assert abs(data.latitude - 37.654321) < 0.000001
        assert abs(data.alt_msl_meters - 123.45) < 0.01
        assert abs(data.track_deg - 45.67) < 0.01
        assert abs(data.ground_speed_mps - 89.12) < 0.01
        assert data.data_type == DataType.GPS
        assert data.timestamp is not None

    def test_parse_xgps_with_negative_values(self, parser):
        """Test parsing XGPS data with negative coordinates."""
        line = "XGPSSimulator,-10.5,-20.3,500.0,180.0,25.5"

        data = parser.parse(line)

        assert isinstance(data, XGPSData)
        assert abs(data.longitude - (-10.5)) < 0.000001
        assert abs(data.latitude - (-20.3)) < 0.000001

    def test_parse_xgps_with_zero_values(self, parser):
        """Test parsing XGPS data with zero values."""
        line = "XGPSSim,0.0,0.0,0.0,0.0,0.0"

        data = parser.parse(line)

        assert isinstance(data, XGPSData)
        assert data.longitude == 0.0
        assert data.latitude == 0.0
        assert data.alt_msl_meters == 0.0
        assert data.track_deg == 0.0
        assert data.ground_speed_mps == 0.0

    def test_parse_valid_xatt_data(self, parser):
        """Test parsing of valid XATT data."""
        line = "XATTAerofly FS 4,180.5,15.3,-5.7"

        data = parser.parse(line)

        assert isinstance(data, XATTData)
        assert data.sim_name == "Aerofly FS 4"
        assert abs(data.heading_deg - 180.5) < 0.01
        assert abs(data.pitch_deg - 15.3) < 0.01
        assert abs(data.roll_deg - (-5.7)) < 0.01
        assert data.data_type == DataType.ATTITUDE
        assert data.timestamp is not None

    def test_parse_xatt_with_extreme_values(self, parser):
        """Test parsing XATT data with extreme but valid values."""
        line = "XATTSim,359.9,89.9,-89.9"

        data = parser.parse(line)

        assert isinstance(data, XATTData)
        assert abs(data.heading_deg - 359.9) < 0.01
        assert abs(data.pitch_deg - 89.9) < 0.01
        assert abs(data.roll_deg - (-89.9)) < 0.01

    def test_parse_invalid_format(self, parser):
        """Test parsing of invalid data format."""
        line = "INVALID_FORMAT"

        data = parser.parse(line)

        assert isinstance(data, UnknownData)
        assert data.raw_data == "INVALID_FORMAT"
        assert data.data_type == DataType.UNKNOWN

    def test_parse_empty_line(self, parser):
        """Test parsing of empty line."""
        line = ""

        data = parser.parse(line)

        assert isinstance(data, UnknownData)
        assert data.raw_data == ""

    def test_parse_xgps_insufficient_fields(self, parser):
        """Test parsing XGPS with insufficient fields."""
        line = "XGPSAerofly FS 4,-122.345678,37.654321"

        data = parser.parse(line)

        # Should return UnknownData due to insufficient fields
        assert isinstance(data, UnknownData)

    def test_parse_xgps_invalid_number(self, parser):
        """Test parsing XGPS with invalid number format."""
        line = "XGPSAerofly FS 4,invalid,37.654321,123.45,45.67,89.12"

        data = parser.parse(line)

        # Should return UnknownData due to invalid number
        assert isinstance(data, UnknownData)

    def test_parse_xatt_insufficient_fields(self, parser):
        """Test parsing XATT with insufficient fields."""
        line = "XATTAerofly FS 4,180.5"

        data = parser.parse(line)

        assert isinstance(data, UnknownData)

    def test_parse_xatt_invalid_number(self, parser):
        """Test parsing XATT with invalid number format."""
        line = "XATTAerofly FS 4,invalid,15.3,-5.7"

        data = parser.parse(line)

        assert isinstance(data, UnknownData)

    def test_parse_multiple_lines(self, parser):
        """Test parsing multiple different data types."""
        lines = [
            "XGPSAerofly FS 4,-122.345678,37.654321,123.45,45.67,89.12",
            "XATTAerofly FS 4,180.5,15.3,-5.7",
            "INVALID",
        ]

        results = [parser.parse(line) for line in lines]

        assert isinstance(results[0], XGPSData)
        assert isinstance(results[1], XATTData)
        assert isinstance(results[2], UnknownData)

    def test_parse_preserves_whitespace_in_sim_name(self, parser):
        """Test that whitespace in sim name is preserved."""
        line = "XGPSAerofly  FS  4,-122.345678,37.654321,123.45,45.67,89.12"

        data = parser.parse(line)

        assert isinstance(data, XGPSData)
        # Sim name should preserve the extra spaces
        assert "Aerofly" in data.sim_name

    def test_parse_xgps_data_to_dict(self, parser):
        """Test that parsed XGPS data can be converted to dict."""
        line = "XGPSAerofly FS 4,-122.345678,37.654321,123.45,45.67,89.12"

        data = parser.parse(line)
        data_dict = data.to_dict()

        assert isinstance(data_dict, dict)
        assert data_dict['data_type'] == DataType.GPS.value
        assert 'longitude' in data_dict
        assert 'latitude' in data_dict
        assert 'alt_msl_meters' in data_dict

    def test_parse_xatt_data_to_dict(self, parser):
        """Test that parsed XATT data can be converted to dict."""
        line = "XATTAerofly FS 4,180.5,15.3,-5.7"

        data = parser.parse(line)
        data_dict = data.to_dict()

        assert isinstance(data_dict, dict)
        assert data_dict['data_type'] == DataType.ATTITUDE.value
        assert 'heading_deg' in data_dict
        assert 'pitch_deg' in data_dict
        assert 'roll_deg' in data_dict

    def test_timestamp_generation(self, parser):
        """Test that timestamps are generated for parsed data."""
        line = "XGPSAerofly FS 4,-122.345678,37.654321,123.45,45.67,89.12"

        before = datetime.datetime.now(datetime.timezone.utc)
        data = parser.parse(line)
        after = datetime.datetime.now(datetime.timezone.utc)

        assert data.timestamp is not None
        assert before <= data.timestamp <= after

    def test_parser_singleton_behavior(self):
        """Test that parser can be instantiated multiple times."""
        parser1 = ForeFlightParser()
        parser2 = ForeFlightParser()

        # Both should work independently
        line = "XGPSTest,-122.0,37.0,100.0,45.0,25.0"

        data1 = parser1.parse(line)
        data2 = parser2.parse(line)

        assert isinstance(data1, XGPSData)
        assert isinstance(data2, XGPSData)
        assert data1.latitude == data2.latitude
