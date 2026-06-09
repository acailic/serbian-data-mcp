"""Configuration management for Serbian Data MCP server."""

from pathlib import Path
from typing import Optional
import json
import os


class Config:
    """Configuration settings for the MCP server."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config.json file. If None, looks in current directory.
        """
        self.config_path = Path(config_path or "config.json")
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from file or use defaults."""
        defaults = {
            "api_base": "https://data.gov.rs",
            "rate_limit": 1.0,
            "timeout": 30,
            "cache_dir": ".cache",
            "export_dir": "exports"
        }

        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    user_config = json.load(f)
                    defaults.update(user_config)
            except (json.JSONDecodeError, IOError):
                pass

        return defaults

    def get(self, key: str, default=None):
        """Get configuration value."""
        return self._config.get(key, default)

    @property
    def api_base(self) -> str:
        """Get API base URL."""
        value = self.get("api_base", "https://data.gov.rs")
        return value if isinstance(value, str) else "https://data.gov.rs"

    @property
    def rate_limit(self) -> float:
        """Get rate limit in seconds."""
        value = self.get("rate_limit", 1.0)
        return value if isinstance(value, (int, float)) else 1.0

    @property
    def timeout(self) -> int:
        """Get timeout in seconds."""
        value = self.get("timeout", 30)
        return value if isinstance(value, int) else 30

    @property
    def cache_dir(self) -> Path:
        """Get cache directory path."""
        value = self.get("cache_dir", ".cache")
        return Path(value if isinstance(value, str) else ".cache")

    @property
    def export_dir(self) -> Path:
        """Get export directory path."""
        value = self.get("export_dir", "exports")
        return Path(value if isinstance(value, str) else "exports")


# Global config instance
config = Config()
