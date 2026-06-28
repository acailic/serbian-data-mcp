"""Configuration management for Serbian Data MCP server."""

from pathlib import Path
from typing import Any, Optional
import logging

import json

from .config_validation import validate_config, ServerConfig

logger = logging.getLogger(__name__)


class Config:
    """Configuration settings for the MCP server with validation."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config.json file. If None, looks in current directory.
        """
        self.config_path = Path(config_path or "config.json")
        self._validated_config: Optional[ServerConfig] = None
        self._config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file or use defaults."""
        defaults = {
            "api_base": "https://data.gov.rs",
            "rate_limit": 1.0,
            "timeout": 30,
            "cache_dir": ".cache",
            "export_dir": "exports",
        }

        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    user_config = json.load(f)

                # Validate user config before merging
                is_valid, error_msg, validated_config = validate_config(user_config)
                if not is_valid:
                    logger.warning(f"Configuration validation failed: {error_msg}. Using defaults for invalid values.")
                    self._validated_config = validate_config(defaults)[2]  # Validate defaults
                else:
                    # User config is valid, merge it with defaults
                    defaults.update(user_config)
                    self._validated_config = validated_config

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load config file {self.config_path}: {e}. Using defaults.")
                # Validate defaults when file loading fails
                self._validated_config = validate_config(defaults)[2]
        else:
            # Validate default configuration
            is_valid, error_msg, validated_config = validate_config(defaults)
            if not is_valid:
                logger.error(f"Default configuration validation failed: {error_msg}")
            else:
                self._validated_config = validated_config

        return defaults

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    def get_validated_config(self) -> Optional[ServerConfig]:
        """Get the validated configuration object if available."""
        return self._validated_config

    def is_valid(self) -> bool:
        """Check if the current configuration is valid."""
        return self._validated_config is not None

    @property
    def api_base(self) -> str:
        """Get API base URL."""
        if self._validated_config:
            url = str(self._validated_config.api_base)
            # Remove trailing slash for backward compatibility
            return url.rstrip("/")
        value = self.get("api_base", "https://data.gov.rs")
        return value if isinstance(value, str) else "https://data.gov.rs"

    @property
    def rate_limit(self) -> float:
        """Get rate limit in seconds."""
        if self._validated_config:
            return self._validated_config.rate_limit
        value = self.get("rate_limit", 1.0)
        return value if isinstance(value, (int, float)) else 1.0

    @property
    def timeout(self) -> int:
        """Get timeout in seconds."""
        if self._validated_config:
            return self._validated_config.timeout
        value = self.get("timeout", 30)
        return value if isinstance(value, int) else 30

    @property
    def cache_dir(self) -> Path:
        """Get cache directory path."""
        if self._validated_config:
            return Path(self._validated_config.cache_dir)
        value = self.get("cache_dir", ".cache")
        return Path(value if isinstance(value, str) else ".cache")

    @property
    def export_dir(self) -> Path:
        """Get export directory path."""
        if self._validated_config:
            return Path(self._validated_config.export_dir)
        value = self.get("export_dir", "exports")
        return Path(value if isinstance(value, str) else "exports")


# Global config instance
config = Config()
