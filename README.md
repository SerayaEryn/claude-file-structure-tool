# File Structure

A Claude Code plugin exposing a `file_structure` MCP tool: a deterministic
structural skeleton (imports + every declaration with its real signature and
line number) for source files. Read a file's shape before opening it.

Built on [tree-sitter](https://tree-sitter.github.io/tree-sitter/) — no LLM, no
hallucination. Unsupported extensions fall back to raw content.

## Install

Requires [`uv`](https://docs.astral.sh/uv/) on `PATH`.

```
/plugin marketplace add SerayaEryn/claude-file-structure-tool
/plugin install file-structure@file-structure
```

## Tool

`file_structure(files: string[], hide_private: bool = false) -> string`

- `files` — paths to digest.
- `hide_private` — omit private/underscore-prefixed declarations.

Paths matched by `.gitignore`/`.aiignore` are refused.

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
| `.groovy`, `.gradle`             | Groovy     |
| `.md`, `.markdown`               | Markdown   |

## License

MIT — see [LICENSE](LICENSE).
