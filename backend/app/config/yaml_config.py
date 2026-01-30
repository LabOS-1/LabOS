"""
YAML Configuration Loader

Loads non-secret application configuration from config/app_config.yaml.
Secrets and passwords remain in .env and cloudbuild.yaml.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml


class YAMLConfigLoader:
    """Load configuration from YAML files."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the YAML config loader.

        Args:
            config_path: Path to the YAML config file. If None, uses default location.
        """
        if config_path is None:
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config" / "app_config.yaml"

        self.config_path = config_path
        self._config: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Dictionary containing configuration data.
        """
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            print(f"⚠️ Config file not found: {self.config_path}")
            return {}

        try:
            with open(self.config_path, 'r') as f:
                self._config = yaml.safe_load(f) or {}
            return self._config
        except Exception as e:
            print(f"❌ Error loading config from {self.config_path}: {e}")
            return {}

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.

        Args:
            key_path: Dot-separated path to the config value (e.g., 'server.port')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        config = self.load()

        keys = key_path.split('.')
        value = config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value


# Global config loader instance
_yaml_config = YAMLConfigLoader()


def load_yaml_config() -> Dict[str, Any]:
    """Load YAML configuration (module-level function)."""
    return _yaml_config.load()


def get_yaml_config(key_path: str, default: Any = None) -> Any:
    """Get a configuration value from YAML using dot notation.

    Args:
        key_path: Dot-separated path (e.g., 'server.port', 'labos.use_mem0')
        default: Default value if not found

    Returns:
        Configuration value or default
    """
    return _yaml_config.get(key_path, default)
