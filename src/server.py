#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "mcp>=1.28",
#   "tree-sitter>=0.26",
#   "tree-sitter-language-pack>=1.13",
#   "pathspec>=1.1",
# ]
# ///
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import structural_digest
from ignore_filter import _is_ignored

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("file-structure")


def _display_path(path):
    try:
        rel = os.path.relpath(path)
    except ValueError:  # e.g. different drive on Windows
        return path
    if rel.startswith(".."):
        return path
    return rel


def _digest_or_raw(path, hide_private=False):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as exc:
        return f"error: {exc}", False

    ext = os.path.splitext(path.lower())[1]
    lang = structural_digest.LANG_BY_EXT.get(ext)
    digest = None
    if lang:
        try:
            digest = structural_digest.build_digest(data, lang, path, hide_private=hide_private)
        except Exception as exc:
            digest = None
            print(f"warning: structural_digest failed for {path}: {exc}", file=sys.stderr)

    if digest:
        return digest, True
    return data.decode("utf-8", errors="ignore"), True


@mcp.tool()
def file_structure(files: list[str], hide_private: bool = False) -> str:
    """Compact structural skeleton of one or more source files: imports plus every
    type/function/field declaration with its exact signature and line span, sliced
    verbatim from source.

    Reach for this FIRST, before Read, whenever you need a file's SHAPE rather than
    its full contents:
    - "where/what is X defined here" - locating a function/class/field to edit
    - getting a line span to aim a precise Read or Edit
    - surveying a file's public API or overall layout
    - scanning several files at once: pass many paths in ONE call

    Each declaration is tagged `L{start}-{end}` (or `L{n}` when it's a single
    line) covering its full body, not just its header - feed that span straight
    into Read(offset=start, limit=end-start+1) instead of reading the whole file.

    Fall back to Read only when you need the actual body of a specific declaration or
    non-declaration content. Falls back to raw file text for unsupported extensions or
    files with no declarations.

    Args:
        files: One or more file paths. Batch related files into a single call.
        hide_private: Omit private/underscore-prefixed declarations for a leaner
            public-API view.
    """
    if isinstance(files, str):
        files = [files]
    if not files:
        return "error: no files given"

    sections = []
    for path in files:
        lines = [f"===== {_display_path(path)} ====="]
        if _is_ignored(path):
            lines.append(f"error: path is ignored (.gitignore/.aiignore): {path}")
        else:
            text, ok = _digest_or_raw(path, hide_private=hide_private)
            lines.append(text)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


if __name__ == "__main__":
    mcp.run()
