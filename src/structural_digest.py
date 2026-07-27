# /// script
# dependencies = [
#   "tree-sitter",
#   "tree-sitter-language-pack",
# ]
# ///
import re
import sys

from specs import LANG_BY_EXT, SPECS

MAX_SIG_LEN = 200
MAX_DIGEST_LINES = 400

_parsers = {}


def _get_parser(lang):
    if lang in _parsers:
        return _parsers[lang]
    from tree_sitter_language_pack import get_parser
    parser = get_parser(lang)
    _parsers[lang] = parser
    return parser


def _node_text(node, content):
    return content[node.start_byte:node.end_byte].decode("utf-8", "ignore")


def _find_body(node, spec):
    body_field = spec.get("body_field")
    if body_field:
        body = node.child_by_field_name(body_field)
        if body is not None:
            return body
    body_types = spec.get("body_types")
    if body_types:
        for child in node.children:
            if child.type in body_types:
                return child
    return None


def _first_brace_start(node):
    # tree-sitter children are always position-ordered, so pre-order DFS
    # visits nodes in increasing start_byte order and the first hit here is
    # the earliest '{' overall.
    for child in node.children:
        if child.type == "{":
            return child.start_byte
        found = _first_brace_start(child)
        if found is not None:
            return found
    return None


def _normalize_sig(raw_text, spec):
    marker = spec.get("comment_marker")
    if marker:
        # A standalone comment line preceding the body's first real
        # statement isn't a body child - it sits between the header and
        # the body node, so it would otherwise leak into the signature.
        lines = raw_text.split("\n")
        for i, line in enumerate(lines[1:], start=1):
            if line.strip().startswith(marker):
                raw_text = "\n".join(lines[:i])
                break
    raw = " ".join(raw_text.split())
    if raw and raw[-1] in "{:;=":
        raw = raw[:-1].rstrip()
    if len(raw) > MAX_SIG_LEN:
        raw = raw[:MAX_SIG_LEN].rstrip() + "…"
    return raw


def _extract_sig(node, content, spec):
    body = _find_body(node, spec)
    if body is not None and spec.get("header_via_brace_scan"):
        # Groovy's `block` node can wrap part of the declaration's own
        # name/args as its own first child (e.g. `class Foo { }`: "class" is
        # a sibling of `block`, but "Foo" sits *inside* it, before the '{').
        # Field/type-based body boundaries don't apply, so instead scan for
        # the first opening brace anywhere in the declaration and slice up
        # to that - wherever the identifier physically nests.
        brace = _first_brace_start(node)
        end = brace if brace is not None else body.end_byte
    else:
        end = body.start_byte if body is not None else node.end_byte
    raw_text = content[node.start_byte:end].decode("utf-8", "ignore")
    return _normalize_sig(raw_text, spec)


def _is_private(sig, spec):
    marker = spec.get("private_marker")
    if marker == "keyword":
        return sig.startswith("#") or re.search(r"\bprivate\b", sig) is not None
    if marker == "underscore":
        m = re.search(r"\bdef\s+(\w+)", sig)
        name = m.group(1) if m else ""
        return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))
    if marker == "pub":
        # Rust: private unless explicitly `pub`/`pub(crate)`/etc. Only
        # applied to func/field signatures (types are never gated), which
        # always carry their own visibility_modifier text when present.
        return re.search(r"\bpub\b", sig) is None
    if marker == "capitalize":
        # Go: exported iff the declared name's first letter is uppercase.
        # Method/function sigs start with "func" (optionally followed by a
        # receiver); field and interface-method sigs start directly with
        # the identifier - try the func-shaped pattern first, else take the
        # leading identifier.
        m = re.match(r"func\s+(?:\([^)]*\)\s*)?(\w+)", sig) or re.match(r"(\w+)", sig)
        name = m.group(1) if m else ""
        return bool(name) and name[0].islower()
    return False


_ARROW_CONST_VALUE_TYPES = {"arrow_function", "function_expression", "function"}


def _arrow_const_sigs(node, content, spec, indent):
    out = []
    for declarator in node.children:
        if declarator.type != "variable_declarator":
            continue
        value = declarator.child_by_field_name("value")
        if value is None or value.type not in _ARROW_CONST_VALUE_TYPES:
            continue
        fn_body = value.child_by_field_name("body")
        end = fn_body.start_byte if fn_body is not None else declarator.end_byte
        raw_text = content[node.start_byte:end].decode("utf-8", "ignore")
        sig = _normalize_sig(raw_text, spec)
        out.append(f"{indent}L{declarator.start_point[0] + 1}: {sig}")
    return out


def _walk(container, spec, content, depth, hide_private=False):
    out = []
    indent = "  " * depth
    for child in container.children:
        t = child.type
        if t in spec.get("unwrap_nodes", ()):
            # `export class Foo`/`declare module X` etc. - the real
            # declaration is one level down; recurse in-place rather than
            # emitting the wrapper itself as a bare "export" line.
            out.extend(_walk(child, spec, content, depth, hide_private))
        elif t in spec["type_nodes"]:
            sig = _extract_sig(child, content, spec)
            out.append(f"{indent}L{child.start_point[0] + 1}: {sig}")
            body = _find_body(child, spec)
            if body is not None:
                out.extend(_walk(body, spec, content, depth + 1, hide_private))
        elif t in spec["func_nodes"]:
            sig = _extract_sig(child, content, spec)
            if hide_private and _is_private(sig, spec):
                continue
            out.append(f"{indent}L{child.start_point[0] + 1}: {sig}")
        elif t in spec.get("field_nodes", ()):
            sig = _extract_sig(child, content, spec)
            if hide_private and _is_private(sig, spec):
                continue
            out.append(f"{indent}L{child.start_point[0] + 1}: field: {sig}")
        elif spec.get("arrow_const") and t in ("lexical_declaration", "variable_declaration"):
            out.extend(_arrow_const_sigs(child, content, spec, indent))
        if len(out) >= MAX_DIGEST_LINES:
            out.append(f"{indent}... [truncated, digest line cap reached]")
            break
    return out


def _first_child_of_type(node, types):
    for child in node.children:
        if child.type in types:
            return child
    return None


def _decl_names(node, content, lang):
    # Kotlin's grammar exposes no field names at all (see SPECS["kotlin"]'s
    # body_field comment) - matched by child type instead of field name.
    if lang == "kotlin":
        if node.type == "property_declaration":
            decl = _first_child_of_type(node, {"variable_declaration"})
            ident = _first_child_of_type(decl, {"simple_identifier"}) if decl is not None else None
        else:
            ident = _first_child_of_type(node, {"type_identifier", "simple_identifier"})
        return [_node_text(ident, content)] if ident is not None else []
    if node.type == "field_declaration" and lang == "java":
        return [
            _node_text(name, content)
            for d in node.children_by_field_name("declarator")
            for name in [d.child_by_field_name("name")] if name is not None
        ]
    if node.type == "field_declaration" and lang == "csharp":
        # C# wraps declarators one level down in a variable_declaration,
        # with no "declarator" field name exposed anywhere - find the
        # variable_declarator children by type instead.
        var_decl = _first_child_of_type(node, {"variable_declaration"})
        if var_decl is None:
            return []
        return [
            _node_text(name, content)
            for d in var_decl.children if d.type == "variable_declarator"
            for name in [d.child_by_field_name("name")] if name is not None
        ]
    named = node.child_by_field_name("name")
    return [_node_text(named, content)] if named is not None else []


def _iter_decls(container, spec, lang, content):
    # Kept separate from _walk (rather than shared) so this can't affect
    # build_digest's existing, heavily-tested output.
    for child in container.children:
        t = child.type
        if t in spec.get("unwrap_nodes", ()):
            yield from _iter_decls(child, spec, lang, content)
        elif t in spec["type_nodes"]:
            for name in _decl_names(child, content, lang):
                yield name, child.start_point[0] + 1
            body = _find_body(child, spec)
            if body is not None:
                yield from _iter_decls(body, spec, lang, content)
        elif t in spec["func_nodes"] or t in spec.get("field_nodes", ()):
            for name in _decl_names(child, content, lang):
                yield name, child.start_point[0] + 1
        elif spec.get("arrow_const") and t in ("lexical_declaration", "variable_declaration"):
            for declarator in child.children:
                if declarator.type != "variable_declarator":
                    continue
                value = declarator.child_by_field_name("value")
                if value is None or value.type not in _ARROW_CONST_VALUE_TYPES:
                    continue
                named = declarator.child_by_field_name("name")
                if named is not None:
                    yield _node_text(named, content), declarator.start_point[0] + 1


def find_declarations(content, lang, name):
    if lang in ("markdown", "groovy"):
        return None
    spec = SPECS.get(lang)
    if spec is None:
        return None
    try:
        parser = _get_parser(lang)
    except Exception:
        return None
    tree = parser.parse(content)
    return [line for found, line in _iter_decls(tree.root_node, spec, lang, content) if found == name]


_GROOVY_CLASS_KEYWORDS = re.compile(r"\b(class|interface|enum|trait)\b")
_SPOCK_LABELS = {
    "given", "when", "then", "expect", "where", "setup", "cleanup", "and", "or",
}


def _groovy_header_text(node, content):
    brace = _first_brace_start(node)
    end = brace if brace is not None else node.end_byte
    return content[node.start_byte:end].decode("utf-8", "ignore")


def _groovy_is_class_file(root, content, spec):
    for child in root.children:
        if child.type != "command":
            continue
        block = _find_body(child, spec)
        if block is None:
            continue
        if _GROOVY_CLASS_KEYWORDS.search(_groovy_header_text(child, content)):
            return True
    return False


def _collapse_sig(text):
    # Unlike _normalize_sig, doesn't strip a trailing opener/terminator -
    # Spock labels and where-table rows legitimately end in ':' or a data
    # value that shouldn't be truncated.
    raw = " ".join(text.split())
    if len(raw) > MAX_SIG_LEN:
        raw = raw[:MAX_SIG_LEN].rstrip() + "…"
    return raw


def _spock_label_text(node, content):
    children = node.children
    if len(children) < 2:
        return None
    label_node, splitter = children[0], children[1]
    if splitter.type != "arg_spliter":
        return None
    if _node_text(label_node, content).strip() not in _SPOCK_LABELS:
        return None
    return _collapse_sig(_node_text(node, content))


def _walk_groovy_class(container, spec, content, depth, in_method_body):
    out = []
    indent = "  " * depth
    pending_where = False
    for child in container.children:
        if child.type != "command":
            continue
        block = _find_body(child, spec)
        # A statement's closure argument (`1 * mock.method({ it == x })`) also
        # produces a `block` child in this shallow grammar - indistinguishable
        # from a real class/method body by node type alone. Once we're inside
        # a method, a block child is a closure/inner-block belonging to a
        # statement, never a new declaration - so only treat block-bearing
        # commands as declarations at class-body (or file-root) level.
        if block is not None and not in_method_body:
            sig = _extract_sig(child, content, spec)
            out.append(f"{indent}L{child.start_point[0] + 1}: {sig}")
            is_class = bool(_GROOVY_CLASS_KEYWORDS.search(_groovy_header_text(child, content)))
            out.extend(_walk_groovy_class(block, spec, content, depth + 1, not is_class))
            pending_where = False
        elif in_method_body:
            label = _spock_label_text(child, content)
            if label is not None:
                out.append(f"{indent}L{child.start_point[0] + 1}: {label}")
                pending_where = label.startswith("where")
            elif pending_where:
                sig = _collapse_sig(_node_text(child, content))
                out.append(f"{indent}L{child.start_point[0] + 1}: {sig}")
                pending_where = False
        else:
            sig = _extract_sig(child, content, spec)
            out.append(f"{indent}L{child.start_point[0] + 1}: {sig}")
        if len(out) >= MAX_DIGEST_LINES:
            out.append(f"{indent}... [truncated, digest line cap reached]")
            break
    return out


def _format_header(prefix, pkg, all_imports, notable):
    parts = []
    if pkg:
        parts.append(f"{prefix} {pkg}")
    if all_imports:
        parts.append(f"imports: {_format_import_list(all_imports, notable)}")
    return "; ".join(parts) if parts else None


def _format_import_list(all_imports, notable, shorten=True):
    shown = notable[:5]
    if not shown:
        common = len(all_imports)
        return f"none notable ({common} stdlib/common)"
    shown_out = [".".join(s.split(".")[-2:]) for s in shown] if shorten else shown
    imp_str = ", ".join(shown_out)
    extra = len(notable) - len(shown)
    if extra > 0:
        imp_str += f" (+{extra} more)"
    return imp_str


def _java_header(root, content):
    pkg, imports = None, []
    for child in root.children:
        if child.type == "package_declaration":
            pkg = _node_text(child, content)[len("package "):].rstrip(";").strip()
        elif child.type == "import_declaration":
            txt = _node_text(child, content)
            txt = txt[len("import "):] if txt.startswith("import ") else txt
            imports.append(txt.rstrip(";").strip())
    notable = [i for i in imports if not i.startswith(("java.", "javax."))]
    return _format_header("package", pkg, imports, notable)


def _kotlin_imports(root):
    found = []

    def visit(n):
        if n.type == "import_header":
            found.append(n)
        elif n.type == "import_list":
            for c in n.children:
                visit(c)

    for c in root.children:
        visit(c)
    return found


def _kotlin_header(root, content):
    pkg = None
    for child in root.children:
        if child.type == "package_header":
            txt = _node_text(child, content).strip()
            pkg = txt[len("package "):].strip() if txt.startswith("package") else txt
    imports = []
    for node in _kotlin_imports(root):
        txt = _node_text(node, content).strip()
        imports.append(txt[len("import "):].strip() if txt.startswith("import") else txt)
    notable = [i for i in imports if not i.startswith(("kotlin.", "kotlinx."))]
    return _format_header("package", pkg, imports, notable)


def _python_root_module(import_line):
    tokens = import_line.split()
    if len(tokens) < 2:
        return ""
    mod = tokens[1] if tokens[0] in ("import", "from") else ""
    return mod.split(".")[0]


def _python_header(root, content):
    imports = []
    for child in root.children:
        if child.type in ("import_statement", "import_from_statement"):
            imports.append(" ".join(_node_text(child, content).split()))
    if not imports:
        return None
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    notable = [i for i in imports if _python_root_module(i) not in stdlib]
    return f"imports: {_format_import_list(imports, notable, shorten=False)}"


def _groovy_header(root, content):
    # The grammar exposes no package/import declaration nodes - those lines
    # are ordinary top-level `command`s and already show up inline in the
    # outline body, so there's nothing distinct to summarize here.
    return None


NODE_BUILTINS = {
    "fs", "path", "os", "http", "https", "http2", "net", "url", "util",
    "crypto", "events", "stream", "child_process", "assert", "buffer",
    "querystring", "readline", "zlib", "process", "tty",
}


def _typescript_imports(root, content):
    specifiers = []
    for child in root.children:
        if child.type not in ("import_statement", "export_statement"):
            continue
        source = child.child_by_field_name("source")
        if source is None:
            continue
        specifiers.append(_node_text(source, content).strip("'\"`"))
    return specifiers


def _typescript_header(root, content):
    imports = _typescript_imports(root, content)
    if not imports:
        return None
    notable = [
        i for i in imports
        if not i.startswith("node:") and i not in NODE_BUILTINS
    ]
    return f"imports: {_format_import_list(imports, notable, shorten=False)}"


def _csharp_header(root, content):
    ns, imports = None, []
    for child in root.children:
        if ns is None and child.type in ("namespace_declaration", "file_scoped_namespace_declaration"):
            name = child.child_by_field_name("name")
            ns = _node_text(name, content) if name is not None else None
        elif child.type == "using_directive":
            txt = " ".join(_node_text(child, content).split()).rstrip(";")
            imports.append(txt[len("using "):].strip() if txt.startswith("using ") else txt)
    notable = [i for i in imports if not i.startswith(("System", "static System"))]
    return _format_header("namespace", ns, imports, notable)


def _rust_use_decls(root):
    return [c for c in root.children if c.type == "use_declaration"]


def _rust_header(root, content):
    imports = []
    for node in _rust_use_decls(root):
        txt = " ".join(_node_text(node, content).split()).rstrip(";")
        imports.append(txt[len("use "):].strip() if txt.startswith("use ") else txt)
    if not imports:
        return None
    notable = [i for i in imports if not re.match(r"(pub\s+)?use\s+(std|core|alloc)::", i)]
    return f"imports: {_format_import_list(imports, notable, shorten=False)}"


def _go_import_specs(root):
    specs = []
    for child in root.children:
        if child.type != "import_declaration":
            continue
        for c in child.children:
            if c.type == "import_spec":
                specs.append(c)
            elif c.type == "import_spec_list":
                specs.extend(cc for cc in c.children if cc.type == "import_spec")
    return specs


def _go_header(root, content):
    pkg = None
    for child in root.children:
        if child.type == "package_clause":
            ident = _first_child_of_type(child, {"package_identifier"})
            pkg = _node_text(ident, content) if ident is not None else None
    imports = []
    for spec in _go_import_specs(root):
        path = spec.child_by_field_name("path")
        if path is not None:
            imports.append(_node_text(path, content).strip('"'))
    # Stdlib import paths have no dot in their first segment (e.g. "fmt",
    # "encoding/json"); third-party paths are domain-qualified
    # ("github.com/foo/bar") - a dot there is the signal.
    notable = [i for i in imports if "." in i.split("/")[0]]
    return _format_header("package", pkg, imports, notable)


_HEADER_BUILDERS = {
    "java": _java_header,
    "kotlin": _kotlin_header,
    "python": _python_header,
    "groovy": _groovy_header,
    "typescript": _typescript_header,
    "tsx": _typescript_header,
    "javascript": _typescript_header,
    "csharp": _csharp_header,
    "rust": _rust_header,
    "go": _go_header,
}


def _import_nodes(root, lang):
    if lang == "java":
        return [c for c in root.children if c.type == "import_declaration"]
    if lang == "kotlin":
        return _kotlin_imports(root)
    if lang == "python":
        return [c for c in root.children if c.type in ("import_statement", "import_from_statement")]
    if lang in ("typescript", "tsx", "javascript"):
        return [c for c in root.children if c.type == "import_statement"]
    if lang == "csharp":
        return [c for c in root.children if c.type == "using_directive"]
    if lang == "rust":
        return _rust_use_decls(root)
    if lang == "go":
        return [c for c in root.children if c.type == "import_declaration"]
    return []


def import_line_ranges(content, lang):
    if lang is None:
        return []
    try:
        parser = _get_parser(lang)
    except Exception:
        return []
    root = parser.parse(content).root_node
    return [(n.start_point[0], n.end_point[0] + 1) for n in _import_nodes(root, lang)]


def _markdown_digest(content):
    # No declarations to parse - keep ATX heading lines as the outline.
    out = []
    text = content.decode("utf-8", "ignore")
    for i, line in enumerate(text.split("\n"), start=1):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        out.append(f"L{i}: {stripped}")
        if len(out) >= MAX_DIGEST_LINES:
            out.append("... [truncated, digest line cap reached]")
            break
    if not out:
        return None
    return "\n".join(out)


def build_digest(content, lang, file_path, hide_private=False):
    if lang == "markdown":
        return _markdown_digest(content)
    spec = SPECS.get(lang)
    if spec is None:
        return None
    try:
        parser = _get_parser(lang)
    except Exception:
        return None

    tree = parser.parse(content)
    root = tree.root_node

    if lang == "groovy" and _groovy_is_class_file(root, content, spec):
        body_lines = _walk_groovy_class(root, spec, content, 0, False)
    else:
        body_lines = _walk(root, spec, content, 0, hide_private)
    if not body_lines:
        return None

    header = _HEADER_BUILDERS[lang](root, content)
    lines = [header] if header else []
    lines.extend(body_lines)
    return "\n".join(lines)


if __name__ == "__main__":
    import os

    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <file>", file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    ext = os.path.splitext(path.lower())[1]
    lang = LANG_BY_EXT.get(ext)
    if not lang:
        print(f"no digest support for extension {ext!r}", file=sys.stderr)
        sys.exit(1)
    with open(path, "rb") as f:
        data = f.read()
    result = build_digest(data, lang, path)
    print(result if result is not None else "(no digest - would fall back)")
