"""Language registry: file-extension routing and per-language tree-sitter
node-type configuration for structural_digest.py.

Node type names are best-effort against current tree-sitter grammars for
each language. If a name is wrong or a grammar changes, the affected
declarations are simply never matched - build_digest() then returns None
(no declarations found) and the caller falls back to the LLM path. Wrong
names degrade gracefully, they never crash the hook.
"""

LANG_BY_EXT = {
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".py": "python",
    ".groovy": "groovy",
    ".gradle": "groovy",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".cs": "csharp",
    ".rs": "rust",
    ".go": "go",
    ".md": "markdown",
    ".markdown": "markdown",
}

SPECS = {
    "java": {
        "type_nodes": {
            "class_declaration", "interface_declaration",
            "enum_declaration", "record_declaration",
            "annotation_type_declaration",
        },
        "func_nodes": {"method_declaration", "constructor_declaration"},
        "field_nodes": {"field_declaration"},
        "body_field": "body",
        "comment_marker": "//",
        "private_marker": "keyword",
    },
    "kotlin": {
        "type_nodes": {
            "class_declaration", "object_declaration", "companion_object",
        },
        "func_nodes": {"function_declaration"},
        "field_nodes": {"property_declaration"},
        # tree-sitter-language-pack's Kotlin grammar doesn't expose field
        # names (child_by_field_name always misses) - find the body by
        # node type instead.
        "body_field": None,
        "body_types": {"class_body", "function_body"},
        "comment_marker": "//",
        "private_marker": "keyword",
    },
    "python": {
        "type_nodes": {"class_definition"},
        "func_nodes": {"function_definition"},
        "field_nodes": set(),
        "body_field": "body",
        "comment_marker": "#",
        "private_marker": "underscore",
    },
    "groovy": {
        # The bundled Decodetalkers grammar is a shallow Gradle-DSL grammar:
        # no class/method/field declaration nodes. Every statement is a
        # `command`; a command that owns a `block` child is a config block we
        # recurse into, otherwise it's a leaf call. This yields a best-effort
        # block outline rather than a Java-style type skeleton.
        "type_nodes": {"command"},
        "func_nodes": set(),
        "field_nodes": set(),
        "body_field": None,
        "body_types": {"block"},
        "header_via_brace_scan": True,
        "comment_marker": "//",
    },
}

_TYPESCRIPT_SPEC = {
    "type_nodes": {
        "class_declaration", "abstract_class_declaration",
        "interface_declaration", "enum_declaration",
        "type_alias_declaration", "internal_module", "module",
    },
    "func_nodes": {
        "function_declaration", "function_signature",
        "method_definition", "method_signature",
        "abstract_method_signature",
    },
    "field_nodes": {"public_field_definition", "property_signature"},
    "body_field": "body",
    "comment_marker": "//",
    # `export class Foo`/`export function f`/`declare module X` wrap the real
    # declaration one level up - unwrap them in-place (same depth) rather
    # than emitting the wrapper itself as a bare "export" line.
    "unwrap_nodes": {"export_statement", "ambient_declaration"},
    # Surface `const Foo = (...) => {...}` / `const f = function () {}` at
    # module or class scope - ubiquitous in TS/React and otherwise invisible
    # to the class/function/interface node model above.
    "arrow_const": True,
    "private_marker": "keyword",
}
# Same spec for both grammars - `tsx` is a JSX-aware superset of the plain
# `typescript` grammar with identical node names for everything we look at.
SPECS["typescript"] = _TYPESCRIPT_SPEC
SPECS["tsx"] = _TYPESCRIPT_SPEC

SPECS["javascript"] = {
    "type_nodes": {"class_declaration"},
    "func_nodes": {
        "function_declaration", "method_definition",
        "generator_function_declaration",
    },
    "field_nodes": {"field_definition"},
    "body_field": "body",
    "comment_marker": "//",
    # `export class Foo`/`export function f` wrap the real declaration one
    # level up - unwrap in place, same as TypeScript (no ambient_declaration
    # in plain JS).
    "unwrap_nodes": {"export_statement"},
    # `const Foo = (...) => {...}` at module/class scope - reuses the same
    # arrow-const handling as TypeScript.
    "arrow_const": True,
    "private_marker": "keyword",  # #private fields
}

SPECS["csharp"] = {
    "type_nodes": {
        "class_declaration", "interface_declaration", "struct_declaration",
        "enum_declaration", "record_declaration", "record_struct_declaration",
        "namespace_declaration", "file_scoped_namespace_declaration",
    },
    "func_nodes": {
        "method_declaration", "constructor_declaration", "property_declaration",
    },
    "field_nodes": {"field_declaration", "event_field_declaration"},
    "body_field": "body",
    "comment_marker": "//",
    "private_marker": "keyword",
}

SPECS["rust"] = {
    "type_nodes": {
        "struct_item", "enum_item", "union_item", "trait_item",
        "impl_item", "mod_item",
    },
    # function_signature_item is a trait method declared without a body
    # (`fn hello(&self);`) - _find_body correctly returns None for it since
    # it has no `body` field, so it's emitted as a bare signature line.
    "func_nodes": {"function_item", "function_signature_item"},
    "field_nodes": {"field_declaration"},
    # struct_item/enum_item/union_item/trait_item/impl_item/mod_item/
    # function_item all expose a uniform `body` field (verified against the
    # bundled grammar): field_declaration_list, enum_variant_list, or
    # declaration_list respectively - no per-node-type special-casing needed.
    "body_field": "body",
    "comment_marker": "//",
    "private_marker": "pub",
}

SPECS["go"] = {
    # `type_spec` (not `type_declaration`) is the actual named-type node -
    # unwrap `type_declaration` so `type ( Foo struct {...}; Bar int )`
    # grouped blocks surface each type_spec at the same depth. Likewise
    # `field_declaration_list` is a pure wrapper around a struct's fields,
    # not a declaration itself, so unwrap it in place too.
    "type_nodes": {"type_spec"},
    # method_elem is an interface method signature (`Hello() string`) - it
    # sits directly inside interface_type with no wrapper list, unlike
    # struct fields, so no extra unwrap is needed for it to surface.
    "func_nodes": {"function_declaration", "method_declaration", "method_elem"},
    "field_nodes": {"field_declaration"},
    # function_declaration/method_declaration expose their block via a
    # `body` field. type_spec doesn't (its struct_type/interface_type is
    # under a `type` field instead) - body_field lookup returns None for
    # it and falls through to the body_types node-type match below, same
    # trick as Kotlin.
    "body_field": "body",
    "body_types": {"struct_type", "interface_type"},
    "unwrap_nodes": {"type_declaration", "field_declaration_list"},
    "comment_marker": "//",
    "private_marker": "capitalize",  # unexported == lowercase initial letter
}
