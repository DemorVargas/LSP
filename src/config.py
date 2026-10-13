"""Configuration management for the LSP server."""
from __future__ import annotations
import json
import os
from typing import Any


class ConfigError(Exception):
    pass


class Config:
    """Hierarchical configuration with file, env, and dict support."""

    def __init__(self, config_path: str | None = None):
        self._data: dict[str, Any] = {
            "logging": {
                "level": "info",
                "output": "stderr",
                "format": "json",
            },
            "performance": {
                "cache_size": 128,
                "max_concurrent": 4,
            },
        }
        if config_path is not None:
            self._load_file(config_path)

    def _load_file(self, path: str) -> None:
        if not os.path.exists(path):
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self._merge(self._data, data)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in {path}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value using dot notation (e.g. 'logging.level')."""
        parts = key.split(".")
        node = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def set(self, key: str, value: Any) -> None:
        """Set a config value using dot notation."""
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node:
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    def has(self, key: str) -> bool:
        """Check if a config key exists."""
        parts = key.split(".")
        node = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return True

    def merge(self, other: dict[str, Any], override: bool = True, deep: bool = True) -> None:
        """Merge another dict into the config."""
        if deep:
            self._merge(self._data, other, override)
        else:
            for k, v in other.items():
                if override or k not in self._data:
                    self._data[k] = v

    def to_dict(self) -> dict[str, Any]:
        """Export config as a dict."""
        return dict(self._data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create a Config from a dict."""
        config = cls()
        config._data = dict(data)
        return config

    def load_from_env(self, prefix: str = "MINILSP_") -> None:
        """Load config from environment variables with prefix.

        Maps env vars to config keys using keyword heuristics:
          MINILSP_LOG_LEVEL      -> logging.level
          MINILSP_CACHE_SIZE     -> performance.cache_size
          MINILSP_MAX_CONCURRENT -> performance.max_concurrent
        """
        # Direct env var -> config key mapping
        env_mapping = {
            "LOG_LEVEL": "logging.level",
            "LOG_FORMAT": "logging.format",
            "LOG_OUTPUT": "logging.output",
            "CACHE_SIZE": "performance.cache_size",
            "MAX_CONCURRENT": "performance.max_concurrent",
        }
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            remainder = key[len(prefix):].upper()
            if remainder in env_mapping:
                self.set(env_mapping[remainder], value.lower())

    def save(self, path: str) -> None:
        """Save config to a JSON file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self._data, f, indent=2)

    def _merge(self, target: dict, source: dict, override: bool = True) -> None:
        """Deep merge source into target."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge(target[key], value, override)
            elif override or key not in target:
                target[key] = value
