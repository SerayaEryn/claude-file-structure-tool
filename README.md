# Claude File Structure Tool

[![Tests](https://github.com/SerayaEryn/claude-file-structure-tool/actions/workflows/tests.yml/badge.svg)](https://github.com/SerayaEryn/claude-file-structure-tool/actions/workflows/tests.yml)

A Claude Code plugin exposing a `file_structure` MCP tool: a deterministic
structural skeleton (imports + every declaration with its real signature and
line number) for source files. Read a file's shape before opening it.

Built on [tree-sitter](https://tree-sitter.github.io/tree-sitter/) — no LLM, no
hallucination. Unsupported extensions fall back to raw content.

## Install

Requires [`uv`](https://docs.astral.sh/uv/) on `PATH` — it transparently
installs the plugin's Python dependencies (Python 3.10+) on first run, no
separate setup needed.

```
/plugin marketplace add SerayaEryn/claude-file-structure-tool
/plugin install file-structure@file-structure
```

## Supported languages

| Extension                        | Language   |
|----------------------------------|------------|
| `.java`                          | Java       |
| `.kt`, `.kts`                    | Kotlin     |
| `.py`                            | Python     |
| `.ts`, `.mts`, `.cts`            | TypeScript |
| `.tsx`                           | TSX        |
| `.js`, `.mjs`, `.cjs`, `.jsx`    | JavaScript |
| `.cs`                            | C#         |
| `.rs`                            | Rust       |
| `.go`                            | Go         |
| `.rb`, `.rake`                   | Ruby       |
| `.scala`, `.sc`                  | Scala      |
| `.groovy`, `.gradle`             | Groovy     |
| `.tf`, `.hcl`                    | Terraform (block outline, like Groovy/Gradle) |
| `.md`, `.markdown`               | Markdown   |

## Tool

`file_structure(files: string[], hide_private: bool = false) -> string`

- `files` — paths to digest.
- `hide_private` — omit private/underscore-prefixed declarations.

Paths matched by `.gitignore`/`.aiignore` are refused.

## Example

`file_structure(["src/ignore_filter.py"])` returns:

```
===== src/ignore_filter.py =====
imports: from pathspec import GitIgnoreSpec
L12-17: def _read_lines(path)
L20-62: class IgnoreMatcher
  L24-26: def __init__(self, root)
  L28-44: def _spec_for_dir(self, dir_path)
  L46-62: def is_ignored(self, rel_path_str, is_dir=False)
L68-74: def get_matcher(root)
L77-78: def _is_noise(root, rel_path_str, is_dir=False)
L81-90: def _find_repo_root(path)
L93-96: def _is_ignored(path)
```

Each declaration's `L{start}-{end}` span covers its full body (single-line
declarations collapse to `L{n}`) — feed it straight into a targeted
`Read(offset, limit)` instead of reading the whole file.

## License

MIT — see [LICENSE](LICENSE).
