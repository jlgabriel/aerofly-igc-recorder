"""
Tests for flight data management module.
"""

import pytest
import tempfile
from pathlib import Path
from app.core.flight import FlightData, haversine_distance
from app.data.models import XGPSData


class TestHaversineDistance:
    """Test cases for haversine distance calculation."""

    def test_haversine_zero_distance(self):
        """Test haversine distance between same point."""
        distance = haversine_distance(0.0, 0.0, 0.0, 0.0)
        assert distance == 0.0

    def test_haversine_known_distance(self):
        """Test haversine distance with known values."""
        # Distance from San Francisco to Los Angeles
        # SF: 37.7749° N, 122.4194° W
        # LA: 34.0522° N, 118.2437° W
        distance = haversine_distance(37.7749, -122.4194, 34.0522, -118.2437)

        # Expected distance is approximately 559 km
        assert 550 < distance < 570

    def test_haversine_equator(self):
        """Test haversine along equator."""
        # 1 degree longitude at equator ≈ 111 km
        distance = haversine_distance(0.0, 0.0, 0.0, 1.0)
        assert 110 < distance < 112

    def test_haversine_meridian(self):
        """Test haversine along meridian."""
        # 1 degree latitude ≈ 111 km
        distance = haversine_distance(0.0, 0.0, 1.0, 0.0)
        assert 110 < distance < 112

    def test_haversine_across_dateline(self):
        """Test haversine across international date line."""
        # From 179°E to 179°W should be ~222 km
        distance = haversine_distance(0.0, 179.0, 0.0, -179.0)
        assert 220 < distance < 225

    def test_haversine_negative_coordinates(self):
        """Test haversine with negative coordinates."""
        distance = haversine_distance(-33.9, 18.4, -34.0, 18.5)
        assert distance > 0


class TestFlightData:
    """Test cases for FlightData class."""

    def test_create_empty_flight(self):
        """Test creating an empty flight."""
        flight = FlightData()

        # Flight should use default values from settings
        assert flight.pilot_name is not None
        assert flight.glider_type is not None
        assert flight.glider_id is not None
        assert len(flight.positions) == 0
        assert len(flight.attitudes) == 0

    def test_add_single_position(self):
        """Test adding a single position."""
        flight = FlightData()

        position = XGPSData(
            sim_name="Test",
            longitude=-122.0,
            latitude=37.0,
            alt_msl_meters=500.0,
            track_deg=180.0,
            ground_speed_mps=25.0
        )

        flight.add_position(position)

        assert len(flight.positions) == 1
        assert flight.positions[0] == position

    def test_add_multiple_positions(self):
        """Test adding multiple positions."""
        flight = FlightData()

        for i in range(10):
            position = XGPSData(
                sim_name="Test",
                longitude=-122.0 + i * 0.01,
                latitude=37.0 + i * 0.01,
                alt_msl_meters=500.0 + i * 10,
                track_deg=180.0,
                ground_speed_mps=25.0
            )
            flight.add_position(position)

        assert len(flight.positions) == 10

    def test_calculate_statistics_insufficient_data(self):
        """Test calculating statistics with insufficient data."""
        flight = FlightData()

        # Add only one position
        position = XGPSData(
            sim_name="Test",
            longitude=-122.0,
            latitude=37.0,
            alt_msl_meters=500.0,
            track_deg=180.0,
            ground_speed_mps=25.0
        )
        flight.add_position(position)

        # Should not crash, just log warning
        flight.calculate_statistics()

        assert flight.max_altitude_meters == 0.0
        assert flight.distance_km == 0.0

    def test_calculate_statistics_with_data(self):
        """Test calculating statistics with sufficient data."""
        flight = FlightData()

        # Add positions with varying altitudes and speeds
        positions_data = [
            (37.0, -122.0, 100.0, 10.0),
            (37.01, -122.01, 200.0, 20.0),
            (37.02, -122.02, 150.0, 15.0),
            (37.03, -122.03, 300.0, 30.0),
        ]

        for lat, lon, alt, speed in positions_data:
            position = XGPSData(
                sim_name="Test",
                longitude=lon,
                latitude=lat,
                alt_msl_meters=alt,
                track_deg=180.0,
                ground_speed_mps=speed
            )
            flight.add_position(position)

        flight.calculate_statistics()

        # Check altitude statistics
        assert flight.max_altitude_meters == 300.0
        assert flight.min_altitude_meters == 100.0

        # Check speed statistics
        assert flight.max_speed_mps == 30.0
        assert flight.avg_speed_mps == 18.75  # (10+20+15+30)/4

        # Check distance was calculated
        assert flight.distance_km > 0.0

    def test_distance_calculation(self):
        """Test that distance is calculated correctly."""
        flight = FlightData()

        # Create a flight path with known distance
        # Moving 0.01 degrees (~1.11 km) in latitude, 3 times
        positions_data = [
            (37.00, -122.0, 100.0),
            (37.01, -122.0, 100.0),
            (37.02, -122.0, 100.0),
            (37.03, -122.0, 100.0),
        ]

        for lat, lon, alt in positions_data:
            position = XGPSData(
                sim_name="Test",
                longitude=lon,
                latitude=lat,
                alt_msl_meters=alt,
                track_deg=0.0,
                ground_speed_mps=0.0
            )
            flight.add_position(position)

        flight.calculate_statistics()

        # Total distance should be approximately 3.33 km (3 * 1.11)
        assert 3.2 < flight.distance_km < 3.5

    def test_load_from_igc_file(self):
        """Test loading flight data from an IGC file."""
        # Create a temporary IGC file
        igc_content = """AFLA001
HFDTE010125
HFPLTPILOT:Test Pilot
HFGTYGLIDERTYPE:ASK 21
HFGIDGLIDERID:D-1234
B1012003715200N12230450WA0050000500
B1012103715201N12230449WA0050100501
B1012203715202N12230448WA0050200502
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.igc', delete=False) as f:
            f.write(igc_content)
            temp_file = f.name

        try:
            # Load flight from file
            flight = FlightData(filename=temp_file)

            # Check that positions were loaded
            assert len(flight.positions) == 3

            # Check pilot info
            assert "Test Pilot" in flight.pilot_name
            assert "ASK 21" in flight.glider_type
            assert "D-1234" in flight.glider_id

            # Check first position
            pos = flight.positions[0]
            assert abs(pos.latitude - 37.2533) < 0.01  # 37°15.200'N
            assert abs(pos.longitude - (-122.5075)) < 0.01  # 122°30.450'W
            assert pos.alt_msl_meters == 500

        finally:
            # Clean up temp file
            import os
            os.unlink(temp_file)

    def test_to_dict(self):
        """Test converting flight data to dictionary."""
        flight = FlightData()
        flight.pilot_name = "Test Pilot"
        flight.glider_type = "Test Glider"

        # Add a position
        position = XGPSData(
            sim_name="Test",
            longitude=-122.0,
            latitude=37.0,
            alt_msl_meters=500.0,
            track_deg=180.0,
            ground_speed_mps=25.0
        )
        flight.add_position(position)
        flight.add_position(position)  # Add second for statistics

        flight.calculate_statistics()

        data_dict = flight.to_dict()

        assert isinstance(data_dict, dict)
        assert data_dict['pilot_name'] == "Test Pilot"
        assert data_dict['glider_type'] == "Test Glider"
        assert 'statistics' in data_dict
        assert 'max_altitude_meters' in data_dict['statistics']
        assert 'distance_km' in data_dict['statistics']
