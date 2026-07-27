from specs import LANG_BY_EXT
from structural_digest import build_digest


def test_unsupported_lang_returns_none():
    assert build_digest(b"whatever", "cobol", "x.cob") is None


def test_declaration_free_source_returns_none():
    assert build_digest(b"x = 1\ny = 2\n", "python", "x.py") is None


def test_markdown_without_headings_returns_none():
    assert build_digest(b"no headings here\njust text\n", "markdown", "x.md") is None


def test_markdown_with_headings_returns_digest():
    digest = build_digest(b"# Title\n\nbody\n", "markdown", "x.md")
    assert digest == "L1: # Title"


def test_lang_by_ext_unknown_extension():
    assert LANG_BY_EXT.get(".xyz") is None


def test_lang_by_ext_known_extension():
    assert LANG_BY_EXT.get(".go") == "go"
    assert LANG_BY_EXT.get(".tsx") == "tsx"
