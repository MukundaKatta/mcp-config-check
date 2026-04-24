"""Tests for mcp-config-check."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from mcp_config_check.validator import (
    Severity,
    validate_config_file,
    validate_config_source,
)


def _codes(issues) -> list[str]:
    return [i.code for i in issues]


def _valid_cfg(extra: dict | None = None) -> str:
    cfg = {
        "mcpServers": {
            "fs": {
                "command": "node",
                "args": ["/abs/path/server.js"],
                "env": {"NODE_ENV": "production"},
            }
        }
    }
    if extra:
        cfg["mcpServers"]["fs"].update(extra)
    return json.dumps(cfg)


def test_valid_minimal_stdio() -> None:
    result = validate_config_source(_valid_cfg())
    assert result.ok
    assert result.errors == []


def test_valid_minimal_http() -> None:
    cfg = {
        "mcpServers": {
            "remote": {
                "url": "https://example.com/mcp",
                "headers": {"Authorization": "Bearer abc123"},
            }
        }
    }
    result = validate_config_source(json.dumps(cfg))
    assert result.ok


def test_empty_file() -> None:
    result = validate_config_source("")
    assert "E000" in _codes(result.errors)


def test_invalid_json() -> None:
    result = validate_config_source("{ not json }")
    assert "E000" in _codes(result.errors)


def test_non_object_root() -> None:
    result = validate_config_source("[]")
    assert "E000" in _codes(result.errors)


def test_missing_container() -> None:
    result = validate_config_source('{"foo": "bar"}')
    assert "E030" in _codes(result.errors)


def test_empty_container_warns() -> None:
    result = validate_config_source('{"mcpServers": {}}')
    assert result.ok
    assert "W030" in _codes(result.warnings)


def test_missing_transport() -> None:
    cfg = {"mcpServers": {"no-transport": {"args": ["x"]}}}
    result = validate_config_source(json.dumps(cfg))
    assert "E001" in _codes(result.errors)


def test_conflicting_transport() -> None:
    cfg = {
        "mcpServers": {
            "both": {
                "command": "node",
                "url": "https://example.com/mcp",
            }
        }
    }
    result = validate_config_source(json.dumps(cfg))
    assert "E002" in _codes(result.errors)


def test_invalid_command_type() -> None:
    cfg = {"mcpServers": {"bad": {"command": 42}}}
    result = validate_config_source(json.dumps(cfg))
    assert "E003" in _codes(result.errors)


def test_invalid_args_shape() -> None:
    cfg = {"mcpServers": {"bad": {"command": "node", "args": "not a list"}}}
    result = validate_config_source(json.dumps(cfg))
    assert "E004" in _codes(result.errors)


def test_hardcoded_secret_in_env() -> None:
    cfg = {
        "mcpServers": {
            "leaky": {
                "command": "node",
                "env": {
                    "ANTHROPIC_API_KEY": "sk-ant-api03_ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567_XYZ"
                },
            }
        }
    }
    result = validate_config_source(json.dumps(cfg))
    assert "E007" in _codes(result.errors)


def test_placeholder_value_in_env() -> None:
    cfg = {
        "mcpServers": {
            "placeholder": {
                "command": "node",
                "env": {"API_KEY": "<your-api-key>"},
            }
        }
    }
    result = validate_config_source(json.dumps(cfg))
    assert "E008" in _codes(result.errors)


def test_secret_in_args() -> None:
    cfg = {
        "mcpServers": {
            "leaky-args": {
                "command": "curl",
                "args": ["-H", "Authorization: Bearer ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"],
            }
        }
    }
    result = validate_config_source(json.dumps(cfg))
    assert "E005" in _codes(result.errors)


def test_url_embedded_credentials() -> None:
    cfg = {
        "mcpServers": {
            "embedded": {
                "url": "https://user:pass@example.com/mcp",
            }
        }
    }
    result = validate_config_source(json.dumps(cfg))
    assert "E021" in _codes(result.errors)


def test_plaintext_http_with_auth_header() -> None:
    cfg = {
        "mcpServers": {
            "insecure": {
                "url": "http://example.com/mcp",
                "headers": {"Authorization": "Bearer abc"},
            }
        }
    }
    result = validate_config_source(json.dumps(cfg))
    assert "E022" in _codes(result.errors)


def test_invalid_url_scheme() -> None:
    cfg = {"mcpServers": {"bad": {"url": "ftp://example.com/mcp"}}}
    result = validate_config_source(json.dumps(cfg))
    assert "E020" in _codes(result.errors)


def test_duplicate_server_name_case_insensitive() -> None:
    cfg_text = textwrap.dedent(
        """\
        {
          "mcpServers": {
            "FooBar": {"command": "node"},
            "foobar": {"command": "python"}
          }
        }
        """
    )
    result = validate_config_source(cfg_text)
    assert "E031" in _codes(result.errors)


def test_autoapprove_wildcard_flagged() -> None:
    cfg = {
        "mcpServers": {
            "dangerous": {
                "command": "node",
                "autoApprove": ["*"],
            }
        }
    }
    result = validate_config_source(json.dumps(cfg))
    assert "E100" in _codes(result.errors)


def test_unknown_field_warns() -> None:
    cfg = {
        "mcpServers": {
            "extra": {
                "command": "node",
                "nonsense_field": "whatever",
            }
        }
    }
    result = validate_config_source(json.dumps(cfg))
    assert result.ok
    assert "W900" in _codes(result.warnings)


def test_zed_context_servers_shape_accepted() -> None:
    cfg = {"context_servers": {"zed-srv": {"command": "python", "args": ["srv.py"]}}}
    result = validate_config_source(json.dumps(cfg))
    assert result.ok


def test_validate_config_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    result = validate_config_file(missing)
    assert "E000" in _codes(result.errors)


def test_validate_config_file_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "mcp.json"
    p.write_text(_valid_cfg())
    result = validate_config_file(p)
    assert result.ok
    assert result.path == str(p)


def test_severity_split_on_result() -> None:
    cfg = {"mcpServers": {"oops": {"args": ["x"]}}}  # missing transport
    result = validate_config_source(json.dumps(cfg))
    assert all(i.severity is Severity.ERROR for i in result.errors)
