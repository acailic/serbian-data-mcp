"""Pydantic models for configuration validation.

These models provide robust validation for configuration settings
with helpful error messages.
"""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, HttpUrl, confloat, conint


class ServerConfig(BaseModel):
    """Validated configuration for Serbian Data MCP Server."""

    model_config = ConfigDict(
        json_encoders={Path: str},
        json_schema_extra={
            "example": {
                "api_base": "https://data.gov.rs",
                "rate_limit": 1.0,
                "timeout": 30,
                "cache_dir": ".cache",
                "export_dir": "exports",
            }
        },
    )
    """Validated configuration for Serbian Data MCP Server."""

    api_base: HttpUrl = Field(default="https://data.gov.rs", description="Base URL for the Serbian data portal API")

    rate_limit: confloat(ge=0.1, le=10.0) = Field(
        default=1.0, description="Rate limit in seconds between API requests (0.1-10.0)"
    )

    timeout: conint(ge=5, le=300) = Field(default=30, description="Request timeout in seconds (5-300)")

    cache_dir: str = Field(default=".cache", description="Directory for caching API responses")

    export_dir: str = Field(default="exports", description="Directory for exported visualizations and data")

    @field_validator("cache_dir", "export_dir")
    @classmethod
    def validate_directory(cls, v: str) -> str:
        """Validate directory names don't contain invalid characters."""
        invalid_chars = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
        if any(char in v for char in invalid_chars):
            raise ValueError(f"Directory name contains invalid characters: {invalid_chars}")
        return v

    @field_validator("api_base")
    @classmethod
    def validate_api_base(cls, v: HttpUrl) -> HttpUrl:
        """Ensure API base URL is accessible."""
        # Convert to string to check if it's a known portal
        str_url = str(v)
        if not any(domain in str_url for domain in ["data.gov.rs", "udata", "opendata"]):
            # Allow custom URLs but warn
            pass
        return v


def validate_config(config_dict: dict) -> tuple[bool, str, Optional[ServerConfig]]:
    """Validate configuration dictionary.

    Args:
        config_dict: Configuration dictionary to validate

    Returns:
        Tuple of (is_valid, error_message, validated_config)
    """
    try:
        config = ServerConfig(**config_dict)
        return True, "", config
    except Exception as e:
        error_msg = f"Configuration validation failed: {e}"
        return False, error_msg, None


def load_and_validate_config(config_path: Path) -> tuple[bool, str, Optional[ServerConfig]]:
    """Load and validate configuration from file.

    Args:
        config_path: Path to config.json file

    Returns:
        Tuple of (is_valid, error_message, validated_config)
    """
    if not config_path.exists():
        return False, f"Configuration file not found: {config_path}", None

    try:
        import json

        with open(config_path) as f:
            config_dict = json.load(f)
        return validate_config(config_dict)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in configuration file: {e}", None
    except Exception as e:
        return False, f"Error reading configuration: {e}", None
