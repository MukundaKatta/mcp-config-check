"""mcp-config-check: linter for MCP (Model Context Protocol) config files."""

from mcp_config_check.validator import (
    Issue,
    Severity,
    ValidationResult,
    validate_config_file,
    validate_config_source,
)

__all__ = [
    "Issue",
    "Severity",
    "ValidationResult",
    "validate_config_file",
    "validate_config_source",
]

__version__ = "0.1.0"
