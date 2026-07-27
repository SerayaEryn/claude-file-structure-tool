# /// script
# dependencies = ["pathspec"]
# ///
"""Root-confined .gitignore/.aiignore matching, consolidated from the
claude-local-offload explore_agent's paths.py/ignore.py/config.py.

Only the pieces file_structure needs are kept here (IgnoreMatcher,
_find_repo_root, _is_ignored) - the source modules also carry
LLM-connection settings and root-escape helpers that don't apply to this
MCP server.
"""
import os
from pathlib import Path

from pathspec import GitIgnoreSpec

_IGNORE_FILENAMES = (".gitignore", ".aiignore")


def _read_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().splitlines()
    except OSError:
        return []


class IgnoreMatcher:
    """Answers is_ignored() for paths under one root. Stateful only as a
    cache - construct via get_matcher(root) rather than directly, so
    repeated tool calls within one server process reuse parsed specs."""

    def __init__(self, root):
        self._root = root
        self._specs = {}

    def _spec_for_dir(self, dir_path):
        """Combined gitignore-syntax spec for <dir_path>/.gitignore plus
        <dir_path>/.aiignore (aiignore lines appended after, so an aiignore
        entry can extend or re-include past a .gitignore rule in the same
        directory), or None if the directory has neither file / both are
        empty. Parse failures are treated as "no opinion" (fail-soft) rather
        than raising - a malformed ignore file shouldn't break every tool
        call against the repo."""
        if dir_path in self._specs:
            return self._specs[dir_path]
        lines = []
        for name in _IGNORE_FILENAMES:
            lines.extend(_read_lines(dir_path / name))
        try:
            spec = GitIgnoreSpec.from_lines(lines) if lines else None
        except Exception:
            spec = None
        self._specs[dir_path] = spec
        return spec

    def is_ignored(self, rel_path_str, is_dir=False):
        """rel_path_str is root-relative ('/'-or-os-sep separated). is_dir
        tells a directory pattern (e.g. "build/") whether to match the path
        itself, not just its contents."""
        rel = rel_path_str.strip("/")
        if not rel or rel == ".":
            return False
        parts = Path(rel).parts
        dir_path = self._root
        ignored = False
        for i, part in enumerate(parts):
            spec = self._spec_for_dir(dir_path)
            if spec is not None:
                sub_rel = "/".join(parts[i:])
                check = sub_rel + "/" if is_dir else sub_rel
                result = spec.check_file(check)
                if result.include is not None:
                    ignored = result.include
            dir_path = dir_path / part
        return ignored


_matchers = {}


def get_matcher(root):
    """One IgnoreMatcher per resolved root, cached for the life of the
    process - each tool call parsing every ignore file from scratch would
    waste the exact per-call cost this tool exists to avoid."""
    key = str(Path(root).resolve())
    matcher = _matchers.get(key)
    if matcher is None:
        matcher = IgnoreMatcher(Path(key))
        _matchers[key] = matcher
    return matcher


def _is_noise(root, rel_path_str, is_dir=False):
    """True if a root-relative path is excluded by a .gitignore/.aiignore
    anywhere in its ancestor chain under root."""
    return get_matcher(root).is_ignored(rel_path_str, is_dir=is_dir)


def _find_repo_root(path):
    """Nearest ancestor directory containing .git (the file's repo root),
    else the file's own directory - file_structure takes explicit file args
    with no --root, so ignore-matching needs a root to walk the ancestor
    chain from."""
    d = os.path.dirname(os.path.abspath(path)) or os.sep
    cur = d
    while True:
        if os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return d
        cur = parent


def _is_ignored(path):
    root = _find_repo_root(path)
    rel = os.path.relpath(os.path.abspath(path), root)
    return _is_noise(root, rel)
