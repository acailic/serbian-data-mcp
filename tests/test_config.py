"""Tests for configuration management."""

import pytest
import json
from pathlib import Path
from serbian_data_mcp.config import Config, config


@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file."""
    config_file = tmp_path / "test_config.json"
    test_config = {
        "api_base": "https://test.example.com",
        "rate_limit": 2.0,
        "timeout": 60,
        "cache_dir": "test_cache",
        "export_dir": "test_exports",
    }
    with open(config_file, "w") as f:
        json.dump(test_config, f)
    return config_file


def test_config_defaults():
    """Test default configuration values."""
    test_config = Config(config_path=None)

    assert test_config.api_base == "https://data.gov.rs"
    assert test_config.rate_limit == 1.0
    assert test_config.timeout == 30
    assert test_config.cache_dir == Path(".cache")
    assert test_config.export_dir == Path("exports")


def test_config_from_file(temp_config_file):
    """Test loading configuration from file."""
    test_config = Config(config_path=str(temp_config_file))

    assert test_config.api_base == "https://test.example.com"
    assert test_config.rate_limit == 2.0
    assert test_config.timeout == 60
    assert test_config.cache_dir == Path("test_cache")
    assert test_config.export_dir == Path("test_exports")


def test_config_invalid_file(tmp_path):
    """Test handling of invalid config file."""
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("not valid json")

    test_config = Config(config_path=str(invalid_file))

    # Should fall back to defaults
    assert test_config.api_base == "https://data.gov.rs"
    assert test_config.rate_limit == 1.0


def test_config_get_method():
    """Test the get method with default values."""
    test_config = Config()

    assert test_config.get("nonexistent_key", "default") == "default"
    assert test_config.get("api_base") == "https://data.gov.rs"


def test_global_config_instance():
    """Test the global config instance."""
    assert config is not None
    assert isinstance(config, Config)
    assert config.api_base == "https://data.gov.rs"


def test_config_type_validation():
    """Test type validation in config properties."""
    # Create config with invalid types
    config_with_bad_types = Config()

    # Test that properties handle invalid types gracefully
    assert isinstance(config_with_bad_types.api_base, str)
    assert isinstance(config_with_bad_types.rate_limit, (int, float))
    assert isinstance(config_with_bad_types.timeout, int)
