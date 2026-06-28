"""
odev.memory — Mémoire persistante simple pour contexte projet et tâches.
"""

import json

from .config import MEMORY_FILE

DEFAULT_MEMORY = {
    "project_summary": "",
    "active_tasks": [],
    "notes": [],
}


def load_memory() -> dict:
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


def save_memory(memory: dict) -> None:
    MEMORY_FILE.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")


def set_project_summary(memory: dict, summary: str) -> dict:
    memory["project_summary"] = summary.strip()
    save_memory(memory)
    return memory


def add_note(memory: dict, note: str) -> dict:
    note = note.strip()
    if note:
        memory.setdefault("notes", []).append(note)
        save_memory(memory)
    return memory


def add_task(memory: dict, title: str) -> dict:
    title = title.strip()
    if not title:
        return memory
    tasks = memory.setdefault("active_tasks", [])
    next_id = 1 + max((task.get("id", 0) for task in tasks), default=0)
    tasks.append({"id": next_id, "title": title, "done": False})
    save_memory(memory)
    return memory


def complete_task(memory: dict, task_id: int) -> bool:
    for task in memory.get("active_tasks", []):
        if task.get("id") == task_id:
            task["done"] = True
            save_memory(memory)
            return True
    return False


def prune_completed_tasks(memory: dict) -> dict:
    memory["active_tasks"] = [task for task in memory.get("active_tasks", []) if not task.get("done")]
    save_memory(memory)
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
