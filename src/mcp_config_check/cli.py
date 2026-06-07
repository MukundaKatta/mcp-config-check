"""Command-line entry point for mcp-config-check."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from mcp_config_check import __version__
from mcp_config_check.validator import Severity, ValidationResult, validate_config_file


def _format_human(results: list[ValidationResult]) -> str:
    lines: list[str] = []
    total_errors = 0
    total_warnings = 0
    for r in results:
        if not r.issues:
            lines.append(f"OK  {r.path}")
            continue
        lines.append(f"{r.path}:")
        for i in r.issues:
            where = f" [{i.server}]" if i.server else ""
            lines.append(f"  {i.severity.value:7s} {i.code}{where} {i.message}")
            if i.severity is Severity.ERROR:
                total_errors += 1
            else:
                total_warnings += 1
    lines.append("")
    lines.append(
        f"{len(results)} file(s), {total_errors} error(s), {total_warnings} warning(s)"
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mcp-config-check",
        description="Lint MCP (Model Context Protocol) config files.",
    )
    parser.add_argument("paths", nargs="+", help="MCP config file paths (JSON)")
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only print errors; hide OK lines and warnings",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"mcp-config-check {__version__}",
    )
    args = parser.parse_args(argv)

    results = [validate_config_file(Path(p)) for p in args.paths]

    if args.quiet:
        filtered = [
            ValidationResult(path=r.path, issues=list(r.errors))
            for r in results
            if r.errors
        ]
        if filtered:
            print(_format_human(filtered))
    else:
        print(_format_human(results))

    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
