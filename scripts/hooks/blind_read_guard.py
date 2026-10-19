#!/usr/bin/env python3
"""PreToolUse hook for the `source-checker` subagent (two-key rule, docs/literature-policy.md).

The blind second reader may open only source documents in ``literature/pdfs/``. Everything
else in the repository (data files, specs, tests, notes) may contain the value it is checking.
Claude Code passes the tool call as JSON on stdin; exit code 2 blocks the call and the message
on stderr is shown to the subagent. Standard library only, so it runs without the venv.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path, PurePath

ALLOWED_SUBDIR = PurePath("literature", "pdfs")


def allowed_roots(cwd: str | None) -> list[Path]:
    roots: list[Path] = []
    for base in (os.environ.get("CLAUDE_PROJECT_DIR"), cwd):
        if base:
            roots.append((Path(base) / ALLOWED_SUBDIR).resolve())
    return roots


def is_inside(path: Path, roots: list[Path]) -> bool:
    resolved = path.resolve()
    return any(resolved == root or root in resolved.parents for root in roots)


def candidate_paths(tool_name: str, tool_input: dict, cwd: Path) -> list[Path] | None:
    """Paths the call would read; None when the call cannot be checked (blocked)."""
    if tool_name == "Read":
        file_path = tool_input.get("file_path")
        return [cwd / file_path] if file_path else None
    if tool_name in ("Glob", "Grep"):
        base = cwd / tool_input["path"] if tool_input.get("path") else cwd
        pattern = str(tool_input.get("pattern", "")) if tool_name == "Glob" else ""
        # Glob: the fixed (wildcard-free) prefix of the pattern must stay inside the folder.
        fixed_parts = []
        for part in PurePath(pattern).parts:
            if any(ch in part for ch in "*?[]{}"):
                break
            fixed_parts.append(part)
        target = base.joinpath(*fixed_parts) if fixed_parts else base
        if tool_name == "Glob" and ".." in PurePath(pattern).parts:
            return None
        return [target]
    return []  # other tools (WebFetch, WebSearch) are not file reads


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("blind_read_guard: could not parse hook input", file=sys.stderr)
        return 2
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}
    cwd = Path(event.get("cwd") or os.getcwd())
    paths = candidate_paths(tool_name, tool_input, cwd)
    if paths is None:
        print(
            f"source-checker: cannot verify the {tool_name} target; read only literature/pdfs/.",
            file=sys.stderr,
        )
        return 2
    roots = allowed_roots(str(cwd))
    for path in paths:
        if not is_inside(path, roots):
            print(
                f"source-checker is a blind reader: {tool_name} of '{path}' is not allowed. "
                "Only source documents in literature/pdfs/ may be read; use WebFetch for online sources.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
