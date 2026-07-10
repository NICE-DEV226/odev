"""Skill odev: génération de documentation structurée à partir du code."""

import ast
from pathlib import Path


def get_description():
    return "Génère de la documentation Markdown à partir d'un fichier ou d'un dossier de code source."


def get_schema():
    return {
        "path": {"type": "string", "default": ".", "description": "Chemin du fichier ou dossier à documenter."},
        "depth": {"type": "integer", "default": 2, "description": "Profondeur de récursion si dossier."},
        "include_private": {"type": "boolean", "default": False, "description": "Inclure les membres privés (_*)."},
    }


def _parse_func(node, include_private: bool):
    name = node.name
    if name.startswith("_") and not include_private:
        return None
    doc = ast.get_docstring(node)
    first_line = doc.strip().splitlines()[0] if doc else ""
    sig = _format_sig(node)
    return ("function", name, sig, first_line)


def _format_sig(node):
    args = node.args
    parts = []
    for arg in args.args:
        parts.append(arg.arg)
    parts.extend(f"*{a.arg}" for a in (args.vararg,) if a)
    for arg in args.kwonlyargs:
        parts.append(f"{arg.arg}=...")
    parts.extend(f"**{a.arg}" for a in (args.kwarg,) if a)
    return f"{node.name}({', '.join(parts)})"


def _parse_py(path: Path, include_private: bool) -> list:
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [("error", "", "", f"Erreur syntaxe: {e}")]

    blocks = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Module):
            doc = ast.get_docstring(node)
            if doc:
                blocks.append(("module", path.name, doc.strip().splitlines()[0][:120], ""))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            entry = _parse_func(node, include_private)
            if entry:
                blocks.append(entry)
        elif isinstance(node, ast.ClassDef):
            name = node.name
            if name.startswith("_") and not include_private:
                continue
            doc = ast.get_docstring(node)
            desc = doc.strip().splitlines()[0] if doc else ""
            blocks.append(("class", name, name, desc))
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fname = item.name
                    if fname.startswith("_") and not include_private:
                        continue
                    fdoc = ast.get_docstring(item)
                    fdesc = fdoc.strip().splitlines()[0] if fdoc else ""
                    blocks.append(("method", f"{name}.{fname}", _format_sig(item), fdesc))
    return blocks


def run(ctx, args=None):
    args = args or {}
    path = Path(args.get("path", ".")).expanduser().resolve()
    depth = int(args.get("depth", 2) or 2)
    include_private = bool(args.get("include_private", False))

    if not path.exists():
        return f"Chemin introuvable: {path}"

    lines = [f"# Documentation — `{path.name}`", ""]

    if path.is_file():
        if path.suffix == ".py":
            for kind, name, sig, desc in _parse_py(path, include_private):
                if desc:
                    lines.append(f"- **`{sig}`** — {desc}")
                else:
                    lines.append(f"- **`{sig}`**")
        else:
            lines.append(f"Extension non supportée: `{path.suffix}` (Python uniquement).")
        return "\n".join(lines)

    py_files = sorted(path.rglob("*.py"))
    for f in py_files:
        rel = f.relative_to(path)
        if len(rel.parts) > depth:
            continue
        if any(p.startswith(".") or p == "__pycache__" for p in rel.parts):
            continue

        blocks = _parse_py(f, include_private)
        if not blocks or all(b[0] == "error" for b in blocks):
            continue

        lines.append(f"## `{rel}`")
        for kind, name, sig, desc in blocks:
            if kind == "error":
                lines.append(f"- ⚠ {sig} {desc}")
            elif kind == "module":
                lines.append(f"> Module: {desc}")
            elif kind in ("class",):
                lines.append(f"\n### `{name}`")
                if desc:
                    lines.append(f"> {desc}")
            else:
                if desc:
                    lines.append(f"- **`{sig}`** — {desc}")
                else:
                    lines.append(f"- **`{sig}`**")
        lines.append("")

    return "\n".join(lines) if len(lines) > 2 else "Aucun fichier Python trouvé."
