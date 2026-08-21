#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "tree-sitter>=0.26,<1",
#   "tree-sitter-language-pack>=1.13,<2",
# ]
# ///
"""PreToolUse hook: give Explore agents the file_structure skeleton instead of
a full Read on large files.

Blocks a Read of a >250-line file when called from an Explore subagent and the
file has an extension file_structure can parse, unless the read is already
targeted (offset/limit set). Instead of a bare denial, the block reason
embeds the structural digest itself so no follow-up tool call is needed.
Fails open on anything unexpected — this must never break a legitimate Read.
"""
import json
import os
import sys

# file_structure only parses the languages in structural_digest.LANG_BY_EXT;
# import the canonical set and digest builder so the guard never redirects a
# file the tool can't handle, and can build the same skeleton inline.
# Fail open (empty set / no builder -> guard never denies) if the import
# can't be resolved.
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from structural_digest import LANG_BY_EXT, build_digest
    _SUPPORTED_EXTS = frozenset(LANG_BY_EXT)
except Exception:
    _SUPPORTED_EXTS = frozenset()
    build_digest = None


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


def _read_and_count(path):
    """Read the whole file, returning (data, line_count). line_count is None
    for binary/special files."""
    with open(path, "rb") as f:
        data = f.read()
    if b"\x00" in data:
        return data, None
    return data, data.count(b"\n")


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
        raw, count = _read_and_count(file_path)
    except OSError:
        return _allow()

    if count is None or count <= 250:
        return _allow()

    digest = None
    if build_digest is not None:
        lang = LANG_BY_EXT.get(ext)
        try:
            digest = build_digest(raw, lang, file_path)
        except Exception:
            digest = None

    if digest:
        _deny(
            f"Read blocked: Its structural "
            "skeleton is below — you do not need to call file_structure for "
            f"this file.\n\n{digest}\n\n"
            'Read only the span you need: Read(file_path="'
            f"{file_path}"
            '", offset=<start>, limit=<end - start + 1>).'
        )

    _deny(
        f"{file_path} has {count} lines. Call the "
        "file_structure tool "
        "(mcp__plugin_file-structure_file-structure__file_structure) first"
        ", then Read only "
        "the span you need via Read(offset, limit)."
    )


if __name__ == "__main__":
    main()
