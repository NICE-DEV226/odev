"""
odev.memory — Mémoire persistante pour contexte projet et tâches.
Support JSON global (~/.config/odev/memory.json) et markdown projet (.odev/memory.md).
"""

import json
import re
from pathlib import Path

from .config import MEMORY_FILE

DEFAULT_MEMORY = {
    "project_summary": "",
    "active_tasks": [],
    "notes": [],
}

_project_memory_path: Path = None


def _find_project_md(cwd: str = None) -> Path:
    """Cherche .odev/memory.md dans cwd ou ses parents."""
    start = Path(cwd or ".").resolve()
    for parent in [start] + list(start.parents):
        candidate = parent / ".odev" / "memory.md"
        if candidate.exists():
            return candidate
    return None


def _project_md_path(cwd: str = None) -> Path:
    """Retourne le chemin .odev/memory.md dans cwd."""
    return Path(cwd or ".").resolve() / ".odev" / "memory.md"


def is_project_mode(cwd: str = None) -> bool:
    """True si un .odev/memory.md existe dans cwd ou ses parents."""
    return _find_project_md(cwd) is not None


def _parse_memory_md(text: str) -> dict:
    """Parse un fichier .odev/memory.md en dictionnaire mémoire."""
    memory = dict(DEFAULT_MEMORY)

    section = None
    summary_lines = []
    tasks = []
    notes = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## summary"):
            section = "summary"
            continue
        elif stripped.startswith("## tasks"):
            section = "tasks"
            continue
        elif stripped.startswith("## notes"):
            section = "notes"
            continue
        elif stripped.startswith("## "):
            section = None
            continue

        if section == "summary":
            if stripped:
                summary_lines.append(stripped)
        elif section == "tasks":
            m = re.match(r'^\s*-\s*\[([ xX])\]\s*#(\d+)\s+(.+)$', line)
            if m:
                done = m.group(1).strip().lower() == "x"
                tasks.append({"id": int(m.group(2)), "title": m.group(3).strip(), "done": done})
        elif section == "notes":
            m = re.match(r'^\s*-\s+(.+)$', line)
            if m:
                notes.append(m.group(1).strip())

    if summary_lines:
        memory["project_summary"] = "\n".join(summary_lines).strip()
    if tasks:
        memory["active_tasks"] = tasks
    if notes:
        memory["notes"] = notes

    return memory


def _render_memory_md(memory: dict) -> str:
    """Génère le contenu markdown .odev/memory.md à partir du dictionnaire."""
    lines = ["# odev memory", ""]

    summary = (memory.get("project_summary") or "").strip()
    if summary:
        lines.append("## summary")
        lines.append(summary)
        lines.append("")

    tasks = memory.get("active_tasks", [])
    if tasks:
        lines.append("## tasks")
        for task in tasks:
            status = "x" if task.get("done") else " "
            lines.append(f"- [{status}] #{task.get('id')} {task.get('title')}")
        lines.append("")

    notes = memory.get("notes", [])
    if notes:
        lines.append("## notes")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def load_memory(cwd: str = None) -> dict:
    """Charge la mémoire. Préfère .odev/memory.md (projet), fallback memory.json (global)."""
    global _project_memory_path
    project_file = _find_project_md(cwd)

    if project_file:
        _project_memory_path = project_file
        try:
            text = project_file.read_text(encoding="utf-8")
            return _parse_memory_md(text)
        except Exception:
            pass

    _project_memory_path = None
    memory = dict(DEFAULT_MEMORY)
    if MEMORY_FILE.exists():
        try:
            payload = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                memory.update(payload)
        except Exception:
            pass
    memory["active_tasks"] = list(memory.get("active_tasks", []))
    memory["notes"] = list(memory.get("notes", []))
    return memory


def save_memory(memory: dict, cwd: str = None) -> None:
    """Sauvegarde la mémoire au bon format selon le mode (projet MD ou global JSON)."""
    if _project_memory_path:
        text = _render_memory_md(memory)
        _project_memory_path.parent.mkdir(parents=True, exist_ok=True)
        _project_memory_path.write_text(text, encoding="utf-8")
    else:
        MEMORY_FILE.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")


def init_project(cwd: str = None) -> str:
    """Crée .odev/memory.md vierge dans cwd. Retourne le chemin."""
    base = Path(cwd or ".").resolve()
    target = base / ".odev" / "memory.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        template = "# odev memory\n\n## summary\n\n\n## tasks\n\n\n## notes\n\n\n"
        target.write_text(template, encoding="utf-8")
    global _project_memory_path
    _project_memory_path = target
    return str(target)


def set_project_summary(memory: dict, summary: str, cwd: str = None) -> dict:
    memory["project_summary"] = summary.strip()
    save_memory(memory, cwd)
    return memory


def add_note(memory: dict, note: str, cwd: str = None) -> dict:
    note = note.strip()
    if note:
        memory.setdefault("notes", []).append(note)
        save_memory(memory, cwd)
    return memory


def add_task(memory: dict, title: str, cwd: str = None) -> dict:
    title = title.strip()
    if not title:
        return memory
    tasks = memory.setdefault("active_tasks", [])
    next_id = 1 + max((task.get("id", 0) for task in tasks), default=0)
    tasks.append({"id": next_id, "title": title, "done": False})
    save_memory(memory, cwd)
    return memory


def complete_task(memory: dict, task_id: int, cwd: str = None) -> bool:
    for task in memory.get("active_tasks", []):
        if task.get("id") == task_id:
            task["done"] = True
            save_memory(memory, cwd)
            return True
    return False


def prune_completed_tasks(memory: dict, cwd: str = None) -> dict:
    memory["active_tasks"] = [task for task in memory.get("active_tasks", []) if not task.get("done")]
    save_memory(memory, cwd)
    return memory


def render_memory(memory: dict) -> str:
    lines = []
    summary = (memory.get("project_summary") or "").strip()
    if summary:
        lines.append("Résumé projet:")
        lines.append(summary)
    tasks = memory.get("active_tasks", [])
    if tasks:
        lines.append("")
        lines.append("Tâches actives:")
        for task in tasks:
            status = "✓" if task.get("done") else "•"
            lines.append(f"{status} #{task.get('id')} {task.get('title')}")
    notes = memory.get("notes", [])
    if notes:
        lines.append("")
        lines.append("Notes récentes:")
        for note in notes[-5:]:
            lines.append(f"- {note}")
    return "\n".join(lines).strip()


def build_memory_block(memory: dict) -> str:
    rendered = render_memory(memory)
    if not rendered:
        return ""
    return "Mémoire persistante:\n" + rendered
