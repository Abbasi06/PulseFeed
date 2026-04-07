"""
Security tests for src/config.py.

Covers:
- LLM config: local llama.cpp/Ollama endpoints have safe defaults
- admin_api_key is optional (None by default — callers must set it)
- Default values are safe and well-formed
- Custom env var overrides work correctly
"""

from __future__ import annotations

import os
from unittest.mock import patch

# ── LLM / inference config ────────────────────────────────────────────────────


class TestLlmConfig:
    def test_llm_light_url_defaults_to_host_docker_internal(self) -> None:
        from src.config import Settings

        default = Settings.model_fields["llm_light_url"].default
        assert default and "host.docker.internal" in str(default)

    def test_llm_heavy_url_defaults_to_host_docker_internal(self) -> None:
        from src.config import Settings

        default = Settings.model_fields["llm_heavy_url"].default
        assert default and "host.docker.internal" in str(default)

    def test_llm_api_key_has_non_empty_default(self) -> None:
        """llama.cpp accepts any non-empty string — default must be set."""
        from src.config import Settings

        default = Settings.model_fields["llm_api_key"].default
        assert default, "llm_api_key must have a non-empty default for llama.cpp"

    def test_admin_api_key_is_optional(self) -> None:
        """admin_api_key is None by default; callers must inject a real key."""
        from src.config import Settings

        field = Settings.model_fields["admin_api_key"]
        assert not field.is_required(), "admin_api_key should be optional"
        assert field.default is None


# ── Default values are sane and safe ─────────────────────────────────────────


class TestDefaultValues:
    def test_storage_database_url_defaults_to_postgres(self) -> None:
        from src.config import Settings

        default = Settings.model_fields["storage_database_url"].default
        assert default is not None
        assert str(default).startswith("postgresql://"), (
            "STORAGE_DATABASE_URL default must be a valid PostgreSQL URI"
        )

    def test_redis_url_defaults_to_redis_scheme(self) -> None:
        from src.config import Settings

        default = Settings.model_fields["redis_url"].default
        assert default is not None
        assert str(default).startswith("redis://"), (
            "REDIS_URL default must be a valid Redis URI"
        )

    def test_admin_api_port_default_is_8001(self) -> None:
        from src.config import Settings

        default = Settings.model_fields["admin_api_port"].default
        assert default == 8001

    def test_admin_api_port_default_in_valid_range(self) -> None:
        from src.config import Settings

        default = Settings.model_fields["admin_api_port"].default
        assert isinstance(default, int)
        assert 1024 <= default <= 65535, (
            f"admin_api_port default {default} is outside safe port range [1024, 65535]"
        )

    def test_generator_db_path_default_is_non_empty(self) -> None:
        from src.config import Settings

        default = Settings.model_fields["generator_db_path"].default
        assert default, "generator_db_path must have a non-empty default"

    def test_github_token_optional_defaults_to_none(self) -> None:
        from src.config import Settings

        field = Settings.model_fields["github_token"]
        assert not field.is_required(), "github_token should be optional"
        assert field.default is None

    def test_gatekeeper_min_confidence_is_within_0_1(self) -> None:
        from src.config import Settings

        default = Settings.model_fields["gatekeeper_min_confidence"].default
        assert 0.0 <= default <= 1.0, (
            f"gatekeeper_min_confidence default {default} is outside [0.0, 1.0]"
        )

    def test_harvest_target_per_source_is_positive_integer(self) -> None:
        from src.config import Settings

        default = Settings.model_fields["harvest_target_per_source"].default
        assert isinstance(default, int)
        assert default > 0, "harvest_target_per_source must be positive"


# ── Env var override works correctly ─────────────────────────────────────────


class TestEnvVarOverride:
    def test_custom_llm_api_key_accepted(self) -> None:
        with patch.dict(os.environ, {"LLM_API_KEY": "my-custom-llama-key"}):
            from src.config import Settings

            s = Settings()
            assert s.llm_api_key == "my-custom-llama-key"

    def test_custom_storage_url_accepted(self) -> None:
        with patch.dict(os.environ, {"STORAGE_DATABASE_URL": "postgresql://user:pw@host:5432/db"}):
            from src.config import Settings

            s = Settings()
            assert s.storage_database_url == "postgresql://user:pw@host:5432/db"

    def test_custom_generator_db_path_accepted(self) -> None:
        with patch.dict(os.environ, {"GENERATOR_DB_PATH": "/tmp/custom_test.db"}):
            from src.config import Settings

            s = Settings()
            assert s.generator_db_path == "/tmp/custom_test.db"

    def test_custom_admin_port_accepted(self) -> None:
        with patch.dict(os.environ, {"ADMIN_API_PORT": "9001"}):
            from src.config import Settings

            s = Settings()
            assert s.admin_api_port == 9001

    def test_custom_redis_url_accepted(self) -> None:
        with patch.dict(os.environ, {"REDIS_URL": "redis://myhost:6380/1"}):
            from src.config import Settings

            s = Settings()
            assert s.redis_url == "redis://myhost:6380/1"

    def test_extra_env_vars_ignored(self) -> None:
        """Unknown env vars must not cause Settings() to fail (extra='ignore')."""
        with patch.dict(os.environ, {"UNKNOWN_VAR_SHOULD_BE_IGNORED": "some_value"}):
            from src.config import Settings

            s = Settings()  # must not raise
            assert s is not None


# ── Celery / MCP command defaults are not obviously injectable ───────────────


class TestCommandDefaults:
    def test_mcp_sql_command_uses_python(self) -> None:
        from src.config import Settings

        cmd = Settings.model_fields["mcp_sql_command"].default
        assert cmd and "python" in str(cmd), "MCP SQL command should invoke python"

    def test_mcp_storage_command_uses_python(self) -> None:
        from src.config import Settings

        cmd = Settings.model_fields["mcp_storage_command"].default
        assert cmd and "python" in str(cmd), "MCP storage command should invoke python"

    def test_mcp_commands_do_not_use_shell_eval(self) -> None:
        """Shell metacharacters in default MCP commands would allow injection."""
        from src.config import Settings

        for field_name in ("mcp_sql_command", "mcp_storage_command"):
            cmd = str(Settings.model_fields[field_name].default or "")
            for dangerous in (";", "&&", "||", "`", "$(", ">", "<", "|"):
                assert dangerous not in cmd, (
                    f"{field_name} default contains shell metachar {dangerous!r}: {cmd!r}"
                )
