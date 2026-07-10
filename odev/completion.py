"""
odev.completion — Auto-complétion Tab pour @fichier, #tâche, /chemin.
Utilise readline pour intercepter Tab dans le prompt utilisateur.
"""

import os
import re
from pathlib import Path

try:
    import readline
except ImportError:
    readline = None

_completion_matches = []
_memory_store = {}


def setup(cwd: str = ".", memory: dict = None):
    """Configure readline avec le completer odev."""
    if readline is None:
        return

    global _memory_store
    _memory_store = memory or {}

    readline.set_completer(_completer)
    readline.set_completer_delims(' \t\n;|&()<>')
    readline.parse_and_bind("tab: complete")


def _completer(text: str, state: int):
    global _completion_matches
    if state == 0:
        line = readline.get_line_buffer()
        _completion_matches = _generate_matches(text, line)
    try:
        return _completion_matches[state]
    except IndexError:
        return None


def _generate_matches(text: str, line: str) -> list:
    if not text and not line.strip():
        return _complete_path(".", "")

    if text.startswith("#"):
        return _complete_tasks(text[1:])
    return _complete_path(text, line)


def _complete_path(text: str, line: str) -> list:
    """
    Complète les chemins fichiers.
    - @fichier → cherche dans le dossier courant
    - chemin/partiel → completion normale
    """
    search = text
    prefix = ""

    if text.startswith("@"):
        prefix = "@"
        search = text[1:]

    if not search:
        search = "."
    elif search.startswith("~"):
        search = str(Path(search).expanduser())

    parent = Path(search).parent if search != "." else Path(".")
    partial = Path(search).name if search != "." else ""

    if not parent.exists():
        return []

    try:
        candidates = []
        for entry in parent.iterdir():
            name = entry.name
            if name.startswith(partial):
                display = name + "/" if entry.is_dir() else name
                full = prefix + str(Path(search).parent / name) if search != "." and search != "@" else prefix + name
                if prefix == "@":
                    full = prefix + name
                candidates.append(full)
        return sorted(candidates)
    except PermissionError:
        return []


def _complete_tasks(text: str) -> list:
    """Complète #id avec les tâches actives."""
    tasks = _memory_store.get("active_tasks", [])
    if not tasks:
        return []

    matches = []
    for task in tasks:
        task_id = str(task.get("id", ""))
        title = task.get("title", "")
        if text and not task_id.startswith(text) and not text in title:
            continue
        matches.append(f"#{task_id}: {title}")
    return matches
