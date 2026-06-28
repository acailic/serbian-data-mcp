"""Tests for configuration management."""

import pytest
import json
from pathlib import Path
from serbian_data_mcp.config import Config, config
from serbian_data_mcp.config_validation import validate_config, ServerConfig


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


def test_config_validation_function():
    """Test the validate_config function."""
    # Valid configuration
    valid_config = {
        "api_base": "https://data.gov.rs",
        "rate_limit": 1.0,
        "timeout": 30,
        "cache_dir": ".cache",
        "export_dir": "exports",
    }
    is_valid, error_msg, validated_config = validate_config(valid_config)
    assert is_valid
    assert not error_msg
    assert isinstance(validated_config, ServerConfig)


def test_config_validation_invalid_rate_limit():
    """Test validation rejects invalid rate limit."""
    invalid_config = {
        "api_base": "https://data.gov.rs",
        "rate_limit": 15.0,  # Too high (max 10.0)
        "timeout": 30,
        "cache_dir": ".cache",
        "export_dir": "exports",
    }
    is_valid, error_msg, validated_config = validate_config(invalid_config)
    assert not is_valid
    assert "rate_limit" in error_msg
    assert validated_config is None


def test_config_validation_invalid_timeout():
    """Test validation rejects invalid timeout."""
    invalid_config = {
        "api_base": "https://data.gov.rs",
        "rate_limit": 1.0,
        "timeout": 2,  # Too low (min 5)
        "cache_dir": ".cache",
        "export_dir": "exports",
    }
    is_valid, error_msg, validated_config = validate_config(invalid_config)
    assert not is_valid
    assert "timeout" in error_msg
    assert validated_config is None


def test_config_validation_invalid_directory():
    """Test validation rejects invalid directory names."""
    invalid_config = {
        "api_base": "https://data.gov.rs",
        "rate_limit": 1.0,
        "timeout": 30,
        "cache_dir": "invalid/dir",  # Contains invalid character
        "export_dir": "exports",
    }
    is_valid, error_msg, validated_config = validate_config(invalid_config)
    assert not is_valid
    assert "cache_dir" in error_msg or "Directory name" in error_msg
    assert validated_config is None


def test_config_validation_invalid_url():
    """Test validation rejects invalid URLs."""
    invalid_config = {
        "api_base": "not-a-url",
        "rate_limit": 1.0,
        "timeout": 30,
        "cache_dir": ".cache",
        "export_dir": "exports",
    }
    is_valid, error_msg, validated_config = validate_config(invalid_config)
    assert not is_valid
    assert "api_base" in error_msg or "URL" in error_msg
    assert validated_config is None


def test_config_validated_methods():
    """Test config validation methods."""
    test_config = Config()

    # Test is_valid method
    assert test_config.is_valid()

    # Test get_validated_config method
    validated = test_config.get_validated_config()
    assert isinstance(validated, ServerConfig)
    assert str(validated.api_base) == "https://data.gov.rs/"
    assert validated.rate_limit == 1.0
    assert validated.timeout == 30


def test_config_with_invalid_file(tmp_path):
    """Test config behavior when loading invalid configuration file."""
    invalid_file = tmp_path / "invalid_config.json"
    invalid_config = {
        "api_base": "https://data.gov.rs",
        "rate_limit": 20.0,  # Invalid: exceeds maximum
        "timeout": 30,
        "cache_dir": ".cache",
        "export_dir": "exports",
    }
    with open(invalid_file, "w") as f:
        json.dump(invalid_config, f)

    # Config should still load but with validation warnings
    test_config = Config(config_path=str(invalid_file))

    # Should fall back to defaults for invalid values
    assert test_config.rate_limit == 1.0  # Default value
    assert test_config.api_base == "https://data.gov.rs"


def test_load_and_validate_config_missing_file(tmp_path):
    """load_and_validate_config returns a not-found envelope for a missing path."""
    from serbian_data_mcp.config_validation import load_and_validate_config

    missing = tmp_path / "does_not_exist.json"
    is_valid, error_msg, validated = load_and_validate_config(missing)

    assert is_valid is False
    assert "Configuration file not found" in error_msg
    assert str(missing) in error_msg
    assert validated is None


def test_load_and_validate_config_valid_file(tmp_path):
    """load_and_validate_config loads + validates a well-formed config file."""
    from serbian_data_mcp.config_validation import load_and_validate_config, ServerConfig

    config_file = tmp_path / "valid_config.json"
    config_file.write_text(
        json.dumps(
            {
                "api_base": "https://data.gov.rs",
                "rate_limit": 1.0,
                "timeout": 30,
                "cache_dir": ".cache",
                "export_dir": "exports",
            }
        )
    )

    is_valid, error_msg, validated = load_and_validate_config(config_file)

    assert is_valid is True
    assert error_msg == ""
    assert isinstance(validated, ServerConfig)


def test_load_and_validate_config_invalid_json(tmp_path):
    """load_and_validate_config maps a JSONDecodeError to the Invalid-JSON envelope."""
    from serbian_data_mcp.config_validation import load_and_validate_config

    config_file = tmp_path / "broken.json"
    config_file.write_text("{not valid json")

    is_valid, error_msg, validated = load_and_validate_config(config_file)

    assert is_valid is False
    assert "Invalid JSON" in error_msg
    assert validated is None


def test_load_and_validate_config_directory_hits_generic_error(tmp_path):
    """Pointing config_path at a directory makes open() raise IsADirectoryError,
    which is NOT a JSONDecodeError so it lands in the generic `except Exception` arm."""
    from serbian_data_mcp.config_validation import load_and_validate_config

    is_valid, error_msg, validated = load_and_validate_config(tmp_path)

    assert is_valid is False
    assert "Error reading configuration" in error_msg
    assert validated is None
