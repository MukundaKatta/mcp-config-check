"""Core validation logic for MCP config files.

Supports both the Claude Desktop / Cursor / Cline / Windsurf shape
(root key ``mcpServers``) and the Zed shape (root key ``context_servers``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcp_config_check.secrets import looks_like_placeholder, looks_like_secret

SERVER_CONTAINERS = ("mcpServers", "context_servers")

ACCEPTED_SERVER_FIELDS = frozenset(
    {
        "command",
        "args",
        "env",
        "cwd",
        "url",
        "headers",
        "transport",
        "type",
        "disabled",
        "alwaysAllow",
        "autoApprove",
        "description",
        "name",
    }
)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    message: str
    server: str | None = None


@dataclass
class ValidationResult:
    path: str
    issues: list[Issue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity is Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]


def _err(code: str, msg: str, server: str | None = None) -> Issue:
    return Issue(Severity.ERROR, code, msg, server)


def _warn(code: str, msg: str, server: str | None = None) -> Issue:
    return Issue(Severity.WARNING, code, msg, server)


def _find_servers(data: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    for key in SERVER_CONTAINERS:
        if key in data and isinstance(data[key], dict):
            return key, data[key]
    return None


def _check_server(name: str, server: Any) -> list[Issue]:
    issues: list[Issue] = []

    if not isinstance(server, dict):
        issues.append(
            _err(
                "E010",
                f"server entry must be an object, got {type(server).__name__}",
                name,
            )
        )
        return issues

    has_command = "command" in server
    has_url = "url" in server

    # E001 missingTransport
    if not has_command and not has_url:
        issues.append(
            _err("E001", "server has no transport (need 'command' or 'url')", name)
        )

    # E002 conflictingTransport
    if has_command and has_url:
        issues.append(
            _err(
                "E002",
                "server declares both 'command' and 'url'; pick one transport",
                name,
            )
        )

    # E003 invalidCommand
    if has_command:
        cmd = server["command"]
        if not isinstance(cmd, str) or not cmd.strip():
            issues.append(_err("E003", "'command' must be a non-empty string", name))

    # E004 invalidArgs
    if "args" in server:
        args = server["args"]
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            issues.append(_err("E004", "'args' must be an array of strings", name))
        else:
            # E005 secretInArgs
            for idx, a in enumerate(args):
                label = looks_like_secret(a)
                if label:
                    issues.append(
                        _err("E005", f"possible {label} hardcoded in args[{idx}]", name)
                    )

    # E006 invalidEnv
    if "env" in server:
        env = server["env"]
        if not isinstance(env, dict):
            issues.append(_err("E006", "'env' must be an object", name))
        else:
            for k, v in env.items():
                if not isinstance(v, str):
                    issues.append(
                        _err(
                            "E006",
                            f"env value for '{k}' must be a string, got {type(v).__name__}",
                            name,
                        )
                    )
                    continue
                # E007 hardcodedSecret
                label = looks_like_secret(v)
                if label:
                    issues.append(
                        _err(
                            "E007",
                            f"possible {label} hardcoded in env['{k}']",
                            name,
                        )
                    )
                # E008 placeholderValue
                if looks_like_placeholder(v):
                    issues.append(
                        _err(
                            "E008",
                            f"env['{k}'] looks like a placeholder ('{v}'); fill it in before running",
                            name,
                        )
                    )

    # URL-based checks
    if has_url:
        url = server["url"]
        if not isinstance(url, str) or not url.strip():
            issues.append(_err("E020", "'url' must be a non-empty string", name))
        else:
            parsed = urlparse(url)
            # E020 invalidUrl
            if parsed.scheme not in ("http", "https"):
                issues.append(
                    _err(
                        "E020",
                        f"'url' scheme '{parsed.scheme or '<none>'}' is not http or https",
                        name,
                    )
                )
            # E021 urlEmbeddedCredentials
            if parsed.username or parsed.password:
                issues.append(
                    _err(
                        "E021",
                        "'url' contains embedded credentials; use headers instead",
                        name,
                    )
                )
            # E022 plaintextHttpWithToken
            if parsed.scheme == "http":
                headers = server.get("headers") or {}
                if isinstance(headers, dict) and any(
                    k.lower() in ("authorization", "x-api-key") for k in headers
                ):
                    issues.append(
                        _err(
                            "E022",
                            "Authorization header sent over plain HTTP; use HTTPS",
                            name,
                        )
                    )

    # W100 autoapproveWildcard
    for approve_key in ("autoApprove", "alwaysAllow"):
        approve = server.get(approve_key)
        if isinstance(approve, list) and "*" in approve:
            issues.append(
                _err(
                    "E100",
                    f"'{approve_key}' contains '*'; this disables all tool confirmations",
                    name,
                )
            )

    # W900 unknownField
    for key in server.keys():
        if key not in ACCEPTED_SERVER_FIELDS:
            issues.append(_warn("W900", f"unknown field '{key}' on server", name))

    return issues


def validate_config_source(source: str, path: str = "<string>") -> ValidationResult:
    """Validate an MCP config given its raw JSON text."""
    result = ValidationResult(path=path)

    if not source.strip():
        result.issues.append(_err("E000", "file is empty"))
        return result

    try:
        data = json.loads(source)
    except json.JSONDecodeError as exc:
        result.issues.append(_err("E000", f"invalid JSON: {exc}"))
        return result

    if not isinstance(data, dict):
        result.issues.append(
            _err("E000", f"root must be a JSON object, got {type(data).__name__}")
        )
        return result

    found = _find_servers(data)
    if found is None:
        result.issues.append(
            _err(
                "E030",
                "no 'mcpServers' (Claude/Cursor/Cline/Windsurf) or 'context_servers' (Zed) object found",
            )
        )
        return result

    container_key, servers = found

    if not servers:
        result.issues.append(
            _warn("W030", f"'{container_key}' is empty; no MCP servers configured")
        )
        return result

    seen_lower: dict[str, str] = {}
    for name, server in servers.items():
        # E031 duplicateServerName (case-insensitive)
        lower = name.lower()
        if lower in seen_lower and seen_lower[lower] != name:
            result.issues.append(
                _err(
                    "E031",
                    f"duplicate server name (case-insensitive): '{name}' vs '{seen_lower[lower]}'",
                    name,
                )
            )
        else:
            seen_lower[lower] = name
        result.issues.extend(_check_server(name, server))

    return result


def validate_config_file(path: str | Path) -> ValidationResult:
    """Validate an MCP config file on disk."""
    p = Path(path)
    if not p.exists():
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"file not found: {p}"))
        return r
    if not p.is_file():
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"not a regular file: {p}"))
        return r
    try:
        source = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        r = ValidationResult(path=str(p))
        r.issues.append(_err("E000", f"file is not valid UTF-8: {exc}"))
        return r
    return validate_config_source(source, path=str(p))
