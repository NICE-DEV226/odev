"""Skill odev: cartographie d'architecture locale."""

import os
import subprocess
from pathlib import Path


def get_description():
    return "Cartographie les modules, points d'entrée, dépendances et fichiers clés d'un projet."


def get_schema():
    return {
        "path": {"type": "string", "default": "."},
        "depth": {"type": "integer", "default": 2},
    }


def _find_entry_points(path: Path) -> list:
    """Trouve les fichiers contenant if __name__ == '__main__'."""
    entries = []
    for py in path.rglob("*.py"):
        if py.stat().st_size > 100_000:
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="replace")
            if '__name__' in text and '__main__' in text:
                rel = py.relative_to(path)
                entries.append(str(rel))
        except Exception:
            pass
    return entries


def _find_config_files(path: Path) -> list:
    patterns = ["*.toml", "*.yaml", "*.yml", "*.json", "*.ini", "*.cfg", "Makefile", "makefile"]
    found = []
    for p in patterns:
        for f in path.glob(p):
            if ".git" not in f.parts:
                found.append(str(f.relative_to(path)))
    return sorted(found)


def _summarize_py_files(path: Path) -> list:
    """Retourne les fichiers Python significatifs avec leur taille et nombre de lignes."""
    files = []
    for py in sorted(path.rglob("*.py")):
        rel = py.relative_to(path)
        if "__pycache__" in rel.parts or ".git" in rel.parts:
            continue
        try:
            lines = py.read_text(encoding="utf-8", errors="replace").splitlines()
            files.append(f"{rel}  ({len(lines)} lignes)")
        except Exception:
            files.append(f"{rel}  (?)")
    return files


def run(ctx, args=None):
    args = args or {}
    path = Path(args.get("path", ".")).expanduser().resolve()
    depth = int(args.get("depth", 2) or 2)

    markers = {
        "pyproject.toml": "Python/pyproject",
        "requirements.txt": "Python/pip",
        "package.json": "Node.js",
        "Cargo.toml": "Rust",
        "go.mod": "Go",
        "README.md": "Documentation",
    }
    stack = [label for filename, label in markers.items() if (path / filename).exists()]

    try:
        tree = subprocess.run(
            [
                "find", str(path),
                "-maxdepth", str(depth),
                "-not", "-path", "*/.git*",
                "-not", "-path", "*/node_modules*",
                "-not", "-path", "*/__pycache__*",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except Exception as exc:
        tree = f"(erreur listing: {exc})"

    entry_points = _find_entry_points(path)
    config_files = _find_config_files(path)
    py_files = _summarize_py_files(path)

    lines = [
        f"Projet: {path}",
        f"Profondeur: {depth}",
        "",
        f"Stack détectée: {', '.join(stack) if stack else 'non détectée'}",
        "",
        "Cartographie:",
        tree or "(vide)",
    ]

    if entry_points:
        lines.extend(["", "Points d'entrée détectés:"])
        lines.extend(f"  - {e}" for e in entry_points[:8])

    if config_files:
        lines.extend(["", "Fichiers de configuration:"])
        lines.extend(f"  - {c}" for c in config_files[:8])

    py_total = len(py_files)
    if py_total > 0:
        lines.extend(["", f"Fichiers Python ({py_total} trouvés):"])
        lines.extend(f"  - {f}" for f in py_files[:20])
        if py_total > 20:
            lines.append(f"  ... et {py_total - 20} autres")

    return "\n".join(lines)
