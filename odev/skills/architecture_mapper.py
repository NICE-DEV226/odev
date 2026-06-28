"""Skill odev: cartographie d'architecture locale."""

import subprocess
from pathlib import Path


def get_description():
    return "Cartographie les modules principaux, les points d'entrée et les dépendances d'un projet."


def get_schema():
    return {
        "path": {"type": "string", "default": "."},
        "depth": {"type": "integer", "default": 2},
    }


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

    return "\n".join([
        f"Projet: {path}",
        f"Profondeur: {depth}",
        "",
        f"Stack détectée: {', '.join(stack) if stack else 'non détectée'}",
        "",
        "Cartographie:",
        tree or "(vide)",
        "",
        "À repérer ensuite:",
        "- Points d'entrée",
        "- Services, routes ou commandes principales",
        "- Modules très couplés",
    ])
