# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning follows [SemVer](https://semver.org/).

## [0.1.0] - 2026-04-23

### Added
- Initial release.
- CLI `mcp-config-check` for validating MCP config files (Claude Desktop, Cursor, Cline, Windsurf, Zed).
- Library API: `validate_config_file`, `validate_config_source`, `ValidationResult`, `Issue`, `Severity`.
- Rules covered in this release: missing/conflicting transport, invalid `command`/`args`/`env` shapes, hardcoded secrets in `env` and `args` (Anthropic/OpenAI/AWS/GitHub/Stripe/Slack/Google/HuggingFace/etc.), placeholder env values, invalid URL scheme, URLs with embedded credentials, Authorization headers over plain HTTP, `autoApprove`/`alwaysAllow` wildcards, case-insensitive duplicate server names, unknown fields.
- Supports both `mcpServers` and `context_servers` root keys.
- GitHub Actions CI on Python 3.9-3.13, and a release workflow that publishes to PyPI via OIDC trusted publishing.
