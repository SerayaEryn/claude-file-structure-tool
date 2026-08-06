from structural_digest import find_declarations
from test_languages import (
    CSHARP_SRC,
    GO_SRC,
    JAVA_SRC,
    RUBY_SRC,
    RUST_SRC,
    SCALA_SRC,
    TERRAFORM_SRC,
)


def test_java_multi_declarator_field_both_names_same_line():
    assert find_declarations(JAVA_SRC, "java", "x") == [7]
    assert find_declarations(JAVA_SRC, "java", "y") == [7]


def test_java_method_name():
    assert find_declarations(JAVA_SRC, "java", "bar") == [10]


def test_java_not_found_returns_empty_list():
    assert find_declarations(JAVA_SRC, "java", "nope") == []


def test_csharp_multi_declarator_field_both_names_same_line():
    assert find_declarations(CSHARP_SRC, "csharp", "x") == [8]
    assert find_declarations(CSHARP_SRC, "csharp", "y") == [8]


def test_csharp_method_name():
    assert find_declarations(CSHARP_SRC, "csharp", "Bar") == [12]


def test_go_struct_field_names():
    assert find_declarations(GO_SRC, "go", "X") == [9]
    assert find_declarations(GO_SRC, "go", "y") == [10]
    assert find_declarations(GO_SRC, "go", "Foo") == [8]


def test_rust_struct_field_names():
    assert find_declarations(RUST_SRC, "rust", "x") == [5]
    assert find_declarations(RUST_SRC, "rust", "y") == [6]
    assert find_declarations(RUST_SRC, "rust", "new") == [10]


def test_scala_class_def_and_val_names():
    assert find_declarations(SCALA_SRC, "scala", "Bar") == [14]
    assert find_declarations(SCALA_SRC, "scala", "greet") == [7, 15]
    assert find_declarations(SCALA_SRC, "scala", "z") == [11]


def test_ruby_class_and_method_names():
    assert find_declarations(RUBY_SRC, "ruby", "Foo") == [5]
    assert find_declarations(RUBY_SRC, "ruby", "bar") == [10]


def test_markdown_and_groovy_and_terraform_have_no_named_declaration_model():
    assert find_declarations(b"# hi", "markdown", "hi") is None
    assert find_declarations(b"plugins { id 'java' }", "groovy", "plugins") is None
    assert find_declarations(TERRAFORM_SRC, "terraform", "web") is None


def test_unsupported_lang_returns_none():
    assert find_declarations(b"whatever", "cobol", "x") is None
