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
    """Print an exact structural skeleton for one or more source files:
    package/imports, then every type/function/field declaration in source
    order with its exact signature (sliced straight from the source, never
    re-synthesized) and its real line number.

    Deterministic tree-sitter extraction - no LLM, no hallucination risk.
    Falls back to raw file content when the extension isn't supported or no
    declarations are found. Use this before opening a file to understand its
    shape cheaply, instead of reading the whole file.

    Args:
        files: One or more file paths to digest.
        hide_private: When true, omit private/underscore-prefixed declarations.
    """
    if isinstance(files, str):
        files = [files]
    if not files:
        return "error: no files given"

    sections = []
    for path in files:
        lines = [f"===== {path} ====="]
        if _is_ignored(path):
            lines.append(f"error: path is ignored (.gitignore/.aiignore): {path}")
        else:
            text, ok = _digest_or_raw(path, hide_private=hide_private)
            lines.append(text)
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


if __name__ == "__main__":
    mcp.run()
