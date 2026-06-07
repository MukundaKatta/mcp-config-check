"""Tests for the command-line entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_config_check.cli import main


def _write(tmp_path: Path, name: str, payload: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_main_exit_zero_on_clean_config(tmp_path: Path, capsys) -> None:
    cfg = {"mcpServers": {"fs": {"command": "node", "args": ["server.js"]}}}
    p = _write(tmp_path, "ok.json", cfg)
    rc = main([str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out


def test_main_exit_one_on_error(tmp_path: Path, capsys) -> None:
    cfg = {"mcpServers": {"broken": {"args": ["x"]}}}  # missing transport
    p = _write(tmp_path, "bad.json", cfg)
    rc = main([str(p)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "E001" in out


def test_main_quiet_hides_ok_lines(tmp_path: Path, capsys) -> None:
    cfg = {"mcpServers": {"fs": {"command": "node"}}}
    p = _write(tmp_path, "ok.json", cfg)
    rc = main(["--quiet", str(p)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" not in out


def test_main_quiet_still_prints_errors(tmp_path: Path, capsys) -> None:
    cfg = {"mcpServers": {"broken": {"args": ["x"]}}}
    p = _write(tmp_path, "bad.json", cfg)
    rc = main(["-q", str(p)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "E001" in out


def test_main_multiple_files_aggregate_exit(tmp_path: Path) -> None:
    good = _write(tmp_path, "good.json", {"mcpServers": {"fs": {"command": "node"}}})
    bad = _write(tmp_path, "bad.json", {"mcpServers": {"x": {"args": ["y"]}}})
    rc = main([str(good), str(bad)])
    assert rc == 1


def test_main_missing_file_reports_error(tmp_path: Path, capsys) -> None:
    rc = main([str(tmp_path / "does-not-exist.json")])
    assert rc == 1
    out = capsys.readouterr().out
    assert "E000" in out


def test_main_version_flag(capsys) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "mcp-config-check" in out
