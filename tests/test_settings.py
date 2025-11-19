"""
Tests for settings module.
"""

import pytest
import os
from app.config.settings import Settings


class TestSettings:
    """Test cases for Settings class."""

    @pytest.fixture(autouse=True)
    def cleanup_settings(self):
        """Clean up settings before and after each test."""
        settings = Settings()
        # Store original values
        original_settings = settings.get_all().copy()

        yield settings

        # Restore original settings manually
        settings._settings = original_settings

    def test_singleton_pattern(self):
        """Test that Settings follows singleton pattern."""
        settings1 = Settings()
        settings2 = Settings()

        assert settings1 is settings2

    def test_default_settings_exist(self):
        """Test that default settings are available."""
        settings = Settings()

        # These settings should exist (may have been modified by other tests)
        assert settings.get('udp_port') is not None
        assert settings.get('recording_interval') is not None
        assert settings.get('default_pilot_name') is not None
        assert settings.get('default_glider_type') is not None
        assert settings.get('default_glider_id') is not None

    def test_get_existing_setting(self):
        """Test getting an existing setting."""
        settings = Settings()
        udp_port = settings.get('udp_port')

        assert udp_port is not None
        assert isinstance(udp_port, int)

    def test_get_nonexistent_setting(self):
        """Test getting a non-existent setting returns None."""
        settings = Settings()
        value = settings.get('nonexistent_key_12345')

        assert value is None

    def test_get_nonexistent_setting_with_default(self):
        """Test getting a non-existent setting with default value."""
        settings = Settings()
        value = settings.get('nonexistent_key_67890', 'default_value')

        assert value == 'default_value'

    def test_set_and_get_setting(self):
        """Test setting and getting a value."""
        settings = Settings()
        unique_key = 'test_key_unique_12345'

        settings.set(unique_key, 'test_value')

        assert settings.get(unique_key) == 'test_value'

    def test_set_overwrite_existing(self):
        """Test overwriting an existing setting."""
        settings = Settings()
        unique_key = 'test_overwrite_key'

        settings.set(unique_key, 'value1')
        assert settings.get(unique_key) == 'value1'

        settings.set(unique_key, 'value2')
        assert settings.get(unique_key) == 'value2'

    def test_save_settings_returns_true(self):
        """Test that save_settings returns True on success."""
        settings = Settings()
        settings.set('test_save_key', 'test_value')

        result = settings.save_settings()

        assert result is True

    def test_get_all_settings(self):
        """Test getting all settings."""
        settings = Settings()
        all_settings = settings.get_all()

        assert isinstance(all_settings, dict)
        assert 'udp_port' in all_settings
        assert 'recording_interval' in all_settings

    def test_multiple_settings_changes(self):
        """Test multiple sequential changes to settings."""
        settings = Settings()

        settings.set('test_key1', 'value1')
        settings.set('test_key2', 'value2')
        settings.set('test_key1', 'updated_value1')

        assert settings.get('test_key1') == 'updated_value1'
        assert settings.get('test_key2') == 'value2'

    def test_setting_different_types(self):
        """Test setting values of different types."""
        settings = Settings()

        settings.set('test_string_val', 'text')
        settings.set('test_int_val', 42)
        settings.set('test_float_val', 3.14)
        settings.set('test_bool_val', True)
        settings.set('test_list_val', [1, 2, 3])
        settings.set('test_dict_val', {'key': 'value'})

        assert settings.get('test_string_val') == 'text'
        assert settings.get('test_int_val') == 42
        assert settings.get('test_float_val') == 3.14
        assert settings.get('test_bool_val') is True
        assert settings.get('test_list_val') == [1, 2, 3]
        assert settings.get('test_dict_val') == {'key': 'value'}

    def test_get_igc_directory(self):
        """Test getting IGC directory path."""
        settings = Settings()
        igc_dir = settings.get('igc_directory')

        assert igc_dir is not None
        assert isinstance(igc_dir, str)
        assert len(igc_dir) > 0
