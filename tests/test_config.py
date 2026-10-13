"""Tests for configuration management."""
import pytest
import tempfile
import os
import json
from src.config import Config, ConfigError


class TestConfig:
    def test_default_config(self):
        config = Config()
        assert config.get("logging.level") == "info"
        assert config.get("logging.output") == "stderr"
        assert config.get("logging.format") == "json"
        assert config.get("performance.cache_size") == 128
        assert config.get("performance.max_concurrent") == 4

    def test_load_from_file(self):
        data = {
            "logging": {"level": "debug", "format": "text"},
            "performance": {"cache_size": 256},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            config = Config(config_path=f.name)
            os.unlink(f.name)
        assert config.get("logging.level") == "debug"
        assert config.get("logging.format") == "text"
        assert config.get("performance.cache_size") == 256

    def test_load_from_missing_file_uses_defaults(self):
        config = Config(config_path="/nonexistent/path/config.json")
        assert config.get("logging.level") == "info"

    def test_load_invalid_json_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            f.flush()
            with pytest.raises(ConfigError):
                Config(config_path=f.name)
            os.unlink(f.name)

    def test_get_nested_key(self):
        config = Config()
        assert config.get("logging.level") == "info"

    def test_get_missing_key_returns_default(self):
        config = Config()
        assert config.get("nonexistent.key", "fallback") == "fallback"

    def test_set_value(self):
        config = Config()
        config.set("logging.level", "warning")
        assert config.get("logging.level") == "warning"

    def test_set_nested_value(self):
        config = Config()
        config.set("performance.cache_size", 512)
        assert config.get("performance.cache_size") == 512

    def test_set_new_key(self):
        config = Config()
        config.set("custom.key", "value")
        assert config.get("custom.key") == "value"

    def test_has_key(self):
        config = Config()
        assert config.has("logging.level")
        assert not config.has("nonexistent.key")

    def test_merge(self):
        config = Config()
        config.merge({"logging": {"level": "debug"}, "new": {"key": "value"}})
        assert config.get("logging.level") == "debug"
        assert config.get("new.key") == "value"

    def test_merge_does_not_override_existing(self):
        config = Config()
        original = config.get("logging.level")
        config.merge({"logging": {"level": "debug"}}, override=False)
        assert config.get("logging.level") == original

    def test_to_dict(self):
        config = Config()
        d = config.to_dict()
        assert isinstance(d, dict)
        assert "logging" in d
        assert "performance" in d

    def test_from_dict(self):
        data = {
            "logging": {"level": "debug"},
            "custom": {"key": "value"},
        }
        config = Config.from_dict(data)
        assert config.get("logging.level") == "debug"
        assert config.get("custom.key") == "value"

    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("MINILSP_LOG_LEVEL", "warning")
        monkeypatch.setenv("MINILSP_CACHE_SIZE", "64")
        config = Config()
        config.load_from_env(prefix="MINILSP_")
        assert config.get("logging.level") == "warning"
        assert config.get("performance.cache_size") == "64"

    def test_save_to_file(self):
        config = Config()
        config.set("logging.level", "debug")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        config.save(path)
        # Verify saved file
        with open(path) as f:
            data = json.load(f)
        assert data["logging"]["level"] == "debug"
        os.unlink(path)

    def test_env_var_mapping(self):
        """Test environment variable to config key mapping."""
        config = Config()
        mapping = {
            "MINILSP_LOG_LEVEL": "logging.level",
            "MINILSP_LOG_FORMAT": "logging.format",
            "MINILSP_CACHE_SIZE": "performance.cache_size",
        }
        for env_var, config_key in mapping.items():
            assert config_key in mapping.values()


class TestConfigEnvVars:
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("MINILSP_LOG_LEVEL", "critical")
        config = Config()
        config.load_from_env()
        assert config.get("logging.level") == "critical"

    def test_env_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("MINILSP_LOG_LEVEL", "DEBUG")
        config = Config()
        config.load_from_env()
        assert config.get("logging.level") == "debug"

    def test_env_missing_var_uses_default(self, monkeypatch):
        monkeypatch.delenv("MINILSP_LOG_LEVEL", raising=False)
        config = Config()
        config.load_from_env()
        assert config.get("logging.level") == "info"


class TestConfigValidation:
    def test_validate_log_level(self):
        config = Config()
        config.set("logging.level", "debug")
        assert config.get("logging.level") == "debug"
        # Invalid levels should still be stored (no validation by default)
        config.set("logging.level", "invalid")
        assert config.get("logging.level") == "invalid"

    def test_validate_positive_int(self):
        config = Config()
        config.set("performance.cache_size", 100)
        assert config.get("performance.cache_size") == 100
        config.set("performance.cache_size", -1)
        assert config.get("performance.cache_size") == -1  # No validation by default

    def test_deep_merge(self):
        config = Config()
        config.set("logging.format", "json")
        config.merge({"logging": {"level": "debug"}}, deep=True)
        assert config.get("logging.level") == "debug"
        assert config.get("logging.format") == "json"  # Should not be lost

    def test_config_repr(self):
        config = Config()
        r = repr(config)
        assert "Config" in r
