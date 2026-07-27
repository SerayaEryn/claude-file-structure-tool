# Claude file-structure Tool

A Claude Code plugin that adds a `file_structure` MCP tool: an exact,
deterministic structural skeleton for one or more source files — package/
imports, then every type/function/field declaration in source order, each
with its real signature (sliced straight from the source, never
re-synthesized) and line number.

Built on [tree-sitter](https://tree-sitter.github.io/tree-sitter/). No LLM
involved, so there's no hallucination risk. Files with an unsupported
extension, or where parsing finds no declarations, fall back to raw file
content.

Use it before opening a file to learn its shape cheaply, instead of reading
the whole thing.

## Supported languages

| Extension | Language |
|---|---|
| `.java` | Java |
| `.kt`, `.kts` | Kotlin |
| `.py` | Python |
| `.ts`, `.mts`, `.cts` | TypeScript |
| `.tsx` | TSX |
| `.groovy`, `.gradle` | Groovy (shallow outline) |
| `.md`, `.markdown` | Markdown (headings only) |

Anything else falls back to raw file content.

## Requirements

[`uv`](https://docs.astral.sh/uv/) on `PATH`. The MCP server is a
`uv run --script` file with inline (PEP 723) dependencies — `uv` resolves
and caches them on first run, no separate install step.

## Install

**Local / development:**

```bash
claude --plugin-dir .
```

**Via marketplace:**

```
/plugin marketplace add .
/plugin install file-structure@file-structure
```

After enabling, `/reload-plugins` picks up changes without restarting.

## Tool

`file_structure(files: string[], hide_private: bool = false) -> string`

- `files` — one or more file paths to digest.
- `hide_private` — when true, omit private/underscore-prefixed declarations.

Paths matched by a `.gitignore`/`.aiignore` (walked from the nearest `.git`
ancestor) are refused rather than read.

## Project layout

```
.claude-plugin/
├── plugin.json        # plugin manifest
└── marketplace.json   # local marketplace descriptor
.mcp.json              # MCP server config
server/
├── server.py            # MCP stdio server (FastMCP)
├── structural_digest.py # tree-sitter extractor
└── ignore_filter.py      # .gitignore/.aiignore matching
```

## License

MIT — see [LICENSE](LICENSE).
