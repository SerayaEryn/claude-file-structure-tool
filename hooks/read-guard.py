#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""PreToolUse hook: nudge Explore agents to file_structure before full reads.

Blocks a Read of a >100-line file when called from an Explore subagent and
the file has an extension file_structure can parse, unless the read is
already targeted (offset/limit set). Fails open on anything unexpected —
this must never break a legitimate Read.
"""
import json
import os
import sys

# file_structure only parses the languages in specs.LANG_BY_EXT; import the
# canonical set so the guard never redirects a file the tool can't handle.
# Fail open (empty set -> guard never denies) if the import can't be resolved.
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from specs import LANG_BY_EXT
    _SUPPORTED_EXTS = frozenset(LANG_BY_EXT)
except Exception:
    _SUPPORTED_EXTS = frozenset()


def _allow():
    sys.exit(0)


def _deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def _line_count(path, limit=100):
    """Count newlines up to limit + 1, streaming in chunks."""
    count = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            if b"\x00" in chunk:
                return None  # binary/special file, skip
            count += chunk.count(b"\n")
            if count > limit:
                return count
    return count


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return _allow()

    if data.get("agent_type") != "Explore":
        return _allow()

    tool_input = data.get("tool_input") or {}
    if tool_input.get("limit") or tool_input.get("offset"):
        return _allow()

    file_path = tool_input.get("file_path")
    if not file_path:
        return _allow()

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in _SUPPORTED_EXTS:
        return _allow()

    try:
        count = _line_count(file_path)
    except OSError:
        return _allow()

    if count is None or count <= 50:
        return _allow()

    _deny(
        f"{file_path} has {count}+ lines. Call the "
        "file_structure tool "
        "(mcp__plugin_file-structure_file-structure__file_structure) first"
        ", then Read only "
        "the span you need via Read(offset, limit)."
    )


if __name__ == "__main__":
    main()
