from structural_digest import build_digest
from test_languages import (
    CSHARP_SRC,
    GO_SRC,
    JAVA_SRC,
    JAVASCRIPT_SRC,
    KOTLIN_SRC,
    PYTHON_SRC,
    RUST_SRC,
    TYPESCRIPT_SRC,
)


def test_java_hide_private_drops_private_field_keeps_public_members():
    digest = build_digest(JAVA_SRC, "java", "Foo.java", hide_private=True)
    assert "field: private int x, y" not in digest
    assert "L8-9: public Foo()" in digest
    assert "L10-11: public void bar()" in digest


def test_csharp_hide_private_drops_private_field_keeps_public_members():
    digest = build_digest(CSHARP_SRC, "csharp", "Foo.cs", hide_private=True)
    assert "field: private int x, y" not in digest
    assert "L9-11: public Foo()" in digest
    assert "L12-14: public void Bar()" in digest


def test_kotlin_hide_private_drops_private_property_keeps_public_fun():
    digest = build_digest(KOTLIN_SRC, "kotlin", "Foo.kt", hide_private=True)
    assert "field: private val x: Int = 0" not in digest
    assert "L7-8: fun bar()" in digest


def test_typescript_hide_private_drops_private_and_hash_fields():
    digest = build_digest(TYPESCRIPT_SRC, "typescript", "foo.ts", hide_private=True)
    assert "field: private x: number = 0" not in digest
    assert "field: #secret: number = 0" not in digest
    assert "L11-12: bar(): void" in digest


def test_javascript_hide_private_drops_hash_field():
    digest = build_digest(JAVASCRIPT_SRC, "javascript", "foo.js", hide_private=True)
    assert "field: #secret = 0" not in digest
    assert "L6-7: bar()" in digest
    assert "L10-11: function baz()" in digest


def test_python_hide_private_drops_underscore_keeps_dunder():
    digest = build_digest(PYTHON_SRC, "python", "foo.py", hide_private=True)
    assert "L9: def _helper(self)" not in digest
    assert "L6-7: def __init__(self)" in digest
    assert "L12-13: def bar(self)" in digest


def test_rust_hide_private_drops_non_pub():
    digest = build_digest(RUST_SRC, "rust", "foo.rs", hide_private=True)
    assert "field: y: i32" not in digest
    assert "L14: fn helper(&self) -> i32" not in digest
    assert "field: pub x: i32" in digest
    assert "L10-12: pub fn new() -> Foo" in digest


def test_go_hide_private_drops_lowercase_initial():
    digest = build_digest(GO_SRC, "go", "foo.go", hide_private=True)
    assert "field: y int" not in digest
    assert "field: X int" in digest
    assert "L17-19: func (f *Foo) Bar() string" in digest
    assert "L21: func helper() int" not in digest
