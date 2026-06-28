"""
odev.sessions — Sauvegarde / chargement / listing de conversations sur disque.
"""

import json
import time
from pathlib import Path

from .config import SESSIONS_DIR


def list_sessions() -> list:
    files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            out.append({
                "name": f.stem,
                "model": data.get("model", "?"),
                "agent_type": data.get("agent_type", "?"),
                "n_messages": len(data.get("messages", [])),
                "updated": data.get("updated", "?"),
            })
        except Exception:
            continue
    return out


def save_session(name: str, model: str, messages: list, agent_type: str = "auto") -> Path:
    fpath = SESSIONS_DIR / f"{name}.json"
    payload = {
        "model": model,
        "messages": messages,
        "agent_type": agent_type,
        "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    fpath.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return fpath


def load_session(name: str):
    fpath = SESSIONS_DIR / f"{name}.json"
    if not fpath.exists():
        return None
    data = json.loads(fpath.read_text(encoding="utf-8"))
    return data.get("model"), data.get("messages", []), data.get("agent_type", "auto")


def delete_session(name: str) -> bool:
    fpath = SESSIONS_DIR / f"{name}.json"
    if fpath.exists():
        fpath.unlink()
        return True
    return False
