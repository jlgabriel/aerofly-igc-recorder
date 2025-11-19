"""
Tests for settings module.
"""

import pytest
import json
import tempfile
from pathlib import Path
from app.config.settings import Settings


class TestSettings:
    """Test cases for Settings class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary directory for config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def settings_instance(self, temp_config_dir):
        """Create a fresh Settings instance with temp directory."""
        # Create a new settings instance pointing to temp directory
        settings = Settings()
        settings.config_dir = temp_config_dir
        settings.config_file = temp_config_dir / "settings.json"
        return settings

    def test_default_settings(self, settings_instance):
        """Test that default settings are loaded correctly."""
        assert settings_instance.get('udp_port') == 49002
        assert settings_instance.get('recording_interval') == 1.0
        assert isinstance(settings_instance.get('default_pilot_name'), str)
        assert isinstance(settings_instance.get('default_glider_type'), str)
        assert isinstance(settings_instance.get('default_glider_id'), str)

    def test_get_existing_setting(self, settings_instance):
        """Test getting an existing setting."""
        udp_port = settings_instance.get('udp_port')
        assert udp_port == 49002

    def test_get_nonexistent_setting(self, settings_instance):
        """Test getting a non-existent setting returns None."""
        value = settings_instance.get('nonexistent_key')
        assert value is None

    def test_get_nonexistent_setting_with_default(self, settings_instance):
        """Test getting a non-existent setting with default value."""
        value = settings_instance.get('nonexistent_key', 'default_value')
        assert value == 'default_value'

    def test_set_setting(self, settings_instance):
        """Test setting a value."""
        settings_instance.set('test_key', 'test_value')
        assert settings_instance.get('test_key') == 'test_value'

    def test_set_overwrite_existing(self, settings_instance):
        """Test overwriting an existing setting."""
        original_port = settings_instance.get('udp_port')
        settings_instance.set('udp_port', 12345)
        assert settings_instance.get('udp_port') == 12345
        assert settings_instance.get('udp_port') != original_port

    def test_save_and_load_settings(self, settings_instance):
        """Test saving and loading settings from file."""
        # Set some custom values
        settings_instance.set('custom_key', 'custom_value')
        settings_instance.set('udp_port', 99999)

        # Save settings
        settings_instance.save_settings()

        # Verify file was created
        assert settings_instance.config_file.exists()

        # Create new instance and load
        new_settings = Settings()
        new_settings.config_dir = settings_instance.config_dir
        new_settings.config_file = settings_instance.config_file
        new_settings.load_settings()

        # Check that custom values were loaded
        assert new_settings.get('custom_key') == 'custom_value'
        assert new_settings.get('udp_port') == 99999

    def test_save_creates_directory(self, temp_config_dir):
        """Test that save_settings creates config directory if needed."""
        # Use a subdirectory that doesn't exist yet
        new_dir = temp_config_dir / "subdir" / "config"

        settings = Settings()
        settings.config_dir = new_dir
        settings.config_file = new_dir / "settings.json"

        settings.set('test', 'value')
        settings.save_settings()

        # Verify directory and file were created
        assert new_dir.exists()
        assert settings.config_file.exists()

    def test_load_invalid_json(self, settings_instance):
        """Test loading settings from invalid JSON file."""
        # Create an invalid JSON file
        settings_instance.config_file.parent.mkdir(parents=True, exist_ok=True)
        settings_instance.config_file.write_text("invalid json {{{")

        # Load settings should handle error gracefully
        settings_instance.load_settings()

        # Should still have default values
        assert settings_instance.get('udp_port') == 49002

    def test_load_nonexistent_file(self, settings_instance):
        """Test loading settings when file doesn't exist."""
        # Ensure file doesn't exist
        if settings_instance.config_file.exists():
            settings_instance.config_file.unlink()

        # Load settings should work with defaults
        settings_instance.load_settings()

        # Should have default values
        assert settings_instance.get('udp_port') == 49002

    def test_settings_persistence(self, settings_instance):
        """Test that settings persist across save/load cycles."""
        test_data = {
            'udp_port': 50000,
            'recording_interval': 2.5,
            'custom_setting': 'test_value',
            'nested_dict': {'key': 'value'},
            'list_value': [1, 2, 3]
        }

        # Set all test data
        for key, value in test_data.items():
            settings_instance.set(key, value)

        # Save
        settings_instance.save_settings()

        # Create new instance and load
        new_settings = Settings()
        new_settings.config_dir = settings_instance.config_dir
        new_settings.config_file = settings_instance.config_file
        new_settings.load_settings()

        # Verify all data persisted
        for key, value in test_data.items():
            assert new_settings.get(key) == value

    def test_get_igc_directory(self, settings_instance):
        """Test getting IGC directory path."""
        igc_dir = settings_instance.get('igc_directory')
        assert igc_dir is not None
        assert isinstance(igc_dir, str)
        # Should contain path separator or be a valid path
        assert len(igc_dir) > 0

    def test_json_file_format(self, settings_instance):
        """Test that saved JSON file is valid and readable."""
        settings_instance.set('test_key', 'test_value')
        settings_instance.save_settings()

        # Read and parse the JSON file directly
        with open(settings_instance.config_file, 'r') as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert 'test_key' in data
        assert data['test_key'] == 'test_value'

    def test_multiple_settings_changes(self, settings_instance):
        """Test multiple sequential changes to settings."""
        # Make multiple changes
        settings_instance.set('key1', 'value1')
        settings_instance.set('key2', 'value2')
        settings_instance.set('key1', 'updated_value1')

        # Verify final state
        assert settings_instance.get('key1') == 'updated_value1'
        assert settings_instance.get('key2') == 'value2'

    def test_setting_different_types(self, settings_instance):
        """Test setting values of different types."""
        settings_instance.set('string_val', 'text')
        settings_instance.set('int_val', 42)
        settings_instance.set('float_val', 3.14)
        settings_instance.set('bool_val', True)
        settings_instance.set('list_val', [1, 2, 3])
        settings_instance.set('dict_val', {'key': 'value'})

        assert settings_instance.get('string_val') == 'text'
        assert settings_instance.get('int_val') == 42
        assert settings_instance.get('float_val') == 3.14
        assert settings_instance.get('bool_val') is True
        assert settings_instance.get('list_val') == [1, 2, 3]
        assert settings_instance.get('dict_val') == {'key': 'value'}
