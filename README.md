# mcp-config-check

[![CI](https://github.com/MukundaKatta/mcp-config-check/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/mcp-config-check/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/mcp-config-check.svg)](https://pypi.org/project/mcp-config-check/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-config-check.svg)](https://pypi.org/project/mcp-config-check/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A small Python linter for [Model Context Protocol](https://modelcontextprotocol.io/) config files used by **Claude Desktop, Cursor, Cline, Windsurf, and Zed**.

It catches common footguns before you start a broken MCP server:

- missing or conflicting transport (no `command` and no `url`, or both set)
- malformed `command` / `args` / `env` shapes
- hardcoded API keys in `env` or `args` (Anthropic, OpenAI, AWS, GitHub, Stripe, Slack, Google, HuggingFace, and more)
- placeholder values left in (`"<your-api-key>"`, `"replace-me"`, etc.)
- URLs with embedded credentials (`https://user:pass@...`)
- auth headers sent over plain HTTP
- `autoApprove: ["*"]` / `alwaysAllow: ["*"]` wildcards that silently disable tool confirmation
- case-insensitive duplicate server names
- unknown fields in a server entry

Supports both the Claude/Cursor/Cline/Windsurf shape (`mcpServers`) and the Zed shape (`context_servers`).

## Install

```bash
pip install mcp-config-check
```

## Usage

```bash
mcp-config-check path/to/mcp.json
```

Multiple files:

```bash
mcp-config-check ~/Library/Application\ Support/Claude/claude_desktop_config.json ~/.cursor/mcp.json
```

Only show errors (no OK lines, no warnings):

```bash
mcp-config-check --quiet path/to/mcp.json
```

Exit status: `0` on no errors, `1` on any errors.

## Use as a library

```python
from mcp_config_check import validate_config_file

result = validate_config_file("path/to/mcp.json")
if not result.ok:
    for issue in result.errors:
        print(issue.code, issue.server, issue.message)
```

## Issue codes

| Code | Severity | Meaning |
|------|----------|---------|
| E000 | error | file-level problem (missing, empty, not JSON, wrong root shape) |
| E001 | error | server has no transport (`command` or `url` required) |
| E002 | error | server declares both `command` and `url` |
| E003 | error | `command` is not a non-empty string |
| E004 | error | `args` is not an array of strings |
| E005 | error | hardcoded secret detected in `args` |
| E006 | error | `env` is not a string-valued object |
| E007 | error | hardcoded secret detected in `env` value |
| E008 | error | `env` value is an obvious placeholder |
| E020 | error | `url` is invalid or has a non-http(s) scheme |
| E021 | error | `url` has embedded credentials |
| E022 | error | Authorization header sent over plain HTTP |
| E030 | error | no `mcpServers` or `context_servers` container found |
| E031 | error | case-insensitive duplicate server name |
| E100 | error | `autoApprove` / `alwaysAllow` contains `"*"` |
| W030 | warning | server container is empty |
| W900 | warning | unknown field on a server entry |

## Use as a GitHub Action

Add this step to any workflow:

```yaml
- uses: actions/checkout@v5
- uses: MukundaKatta/mcp-config-check@v1
  with:
    paths: .mcp.json
```

Pass multiple files space-separated (e.g. `paths: .mcp.json .cursor/mcp.json`). The action runs the same checks as the CLI and fails the workflow on any errors. Inputs: `paths` (required), `quiet` (default `false`), `python-version` (default `3.12`).

## Development

```bash
pip install -e '.[dev]'
pytest
```

## License

MIT