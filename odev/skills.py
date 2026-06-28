"""
odev.skills — Chargement dynamique de skills Python depuis le projet et ~/.config/odev/skills/.
Un skill est un module exposant : get_description() -> str, run(ctx, args) -> str
Optionnel : get_schema() -> dict (propriétés JSON des arguments, sinon objet libre).
"""

import importlib.util
import traceback
from pathlib import Path

from .config import SKILLS_DIR
from .logger import log

SKILLS_REGISTRY: dict = {}
LOCAL_SKILLS_DIR = Path(__file__).resolve().parent / "skills"

_DEFAULT_SKILLS = {
    "sys_info.py": '''# Skill odev : informations système avancées
import platform, os, shutil

def get_description():
    return "Renvoie des métriques matérielles et OS (CPU, charge, disque)."

def run(ctx, args=None):
    try:
        total, used, free = shutil.disk_usage("/")
        cpu_count = os.cpu_count()
        load = os.getloadavg() if hasattr(os, "getloadavg") else "N/A"
        return (
            f"OS: {platform.system()} {platform.release()}\\n"
            f"CPU Cores: {cpu_count}\\n"
            f"Load Avg: {load}\\n"
            f"Disque: {used//(2**30)}Go / {total//(2**30)}Go utilisés ({free//(2**30)}Go libres)"
        )
    except Exception as e:
        return f"Erreur: {e}"
''',
    "search_pattern.py": '''# Skill odev : recherche rapide de motif texte
import subprocess

def get_description():
    return "Recherche récursive d'un pattern regex dans un dossier (via grep)."

def get_schema():
    return {
        "pattern": {"type": "string", "description": "Motif à rechercher."},
        "folder": {"type": "string", "description": "Dossier cible.", "default": "."},
    }

def run(ctx, args=None):
    args = args or {}
    pattern = args.get("pattern", "")
    folder  = args.get("folder", ".")
    if not pattern:
        return "Erreur : paramètre 'pattern' requis."
    try:
        r = subprocess.run(
            ["grep", "-rnw", folder, "-e", pattern, "--max-count=30"],
            capture_output=True, text=True, timeout=15,
        )
        return r.stdout if r.stdout else "Aucun résultat trouvé."
    except Exception as e:
        return f"Erreur: {e}"
''',
    "project_summary.py": '''# Skill odev : résumé rapide d'un projet de code
import subprocess
from pathlib import Path

def get_description():
    return "Donne un aperçu d'un projet : structure, fichiers principaux, stack détectée."

def get_schema():
    return {"path": {"type": "string", "default": "."}}

def run(ctx, args=None):
    path = Path((args or {}).get("path", ".")).expanduser().resolve()
    markers = {
        "package.json": "Node.js/JS",
        "pyproject.toml": "Python (pyproject)",
        "requirements.txt": "Python (pip)",
        "Cargo.toml": "Rust",
        "go.mod": "Go",
        "pom.xml": "Java/Maven",
        "Gemfile": "Ruby",
        "composer.json": "PHP",
    }
    stack = [label for fname, label in markers.items() if (path / fname).exists()]
    try:
        tree = subprocess.run(
            ["find", str(path), "-maxdepth", "2", "-not", "-path", "*/.git*",
             "-not", "-path", "*/node_modules*", "-not", "-path", "*/__pycache__*"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception as e:
        tree = f"(erreur listing: {e})"
    stack_str = ", ".join(stack) if stack else "non détectée"
    return f"Stack détectée : {stack_str}\\n\\nStructure (profondeur 2):\\n{tree}"
''',
}


def _ensure_default_skills():
    for fname, content in _DEFAULT_SKILLS.items():
        fpath = SKILLS_DIR / fname
        if not fpath.exists():
            fpath.write_text(content, encoding="utf-8")


def _iter_skill_files() -> list:
    sources = []
    if LOCAL_SKILLS_DIR.exists():
        sources.append(LOCAL_SKILLS_DIR)
    sources.append(SKILLS_DIR)

    ordered = {}
    for source in sources:
        for filepath in sorted(source.glob("*.py")):
            ordered[filepath.name] = filepath
    return [ordered[name] for name in sorted(ordered)]


def load_skills() -> list:
    SKILLS_REGISTRY.clear()
    _ensure_default_skills()
    loaded, errors = [], []
    for filepath in _iter_skill_files():
        name = filepath.stem
        try:
            spec = importlib.util.spec_from_file_location(f"odev_skill_{filepath.parent.name}_{name}", filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if hasattr(module, "run") and hasattr(module, "get_description"):
                schema = module.get_schema() if hasattr(module, "get_schema") else None
                SKILLS_REGISTRY[name] = {
                    "module": module,
                    "description": module.get_description(),
                    "schema": schema,
                    "file": filepath,
                }
                loaded.append(name)
            else:
                errors.append(f"{name}: doit définir run() et get_description()")
        except Exception as e:
            log.error(f"skill {name}: {e}\n{traceback.format_exc()}")
            errors.append(f"{name}: {e}")
    return loaded, errors


def skill_tool_schemas() -> list:
    schemas = []
    for name, data in SKILLS_REGISTRY.items():
        props = data["schema"] or {"_free": {"type": "string", "description": "Arguments libres (JSON ou texte)."}}
        schemas.append({
            "type": "function",
            "function": {
                "name": f"skill_{name}",
                "description": data["description"],
                "parameters": {"type": "object", "properties": props},
            },
        })
    return schemas


def run_skill(name: str, args: dict) -> str:
    if name not in SKILLS_REGISTRY:
        return f"Skill '{name}' introuvable. Disponibles : {', '.join(SKILLS_REGISTRY) or 'aucun'}"
    try:
        return SKILLS_REGISTRY[name]["module"].run(None, args)
    except Exception as e:
        log.error(f"erreur exécution skill {name}: {e}\n{traceback.format_exc()}")
        return f"Erreur skill '{name}' : {e}"
