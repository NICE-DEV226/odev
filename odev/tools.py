"""
odev.tools — Outils natifs exposés au modèle.
Chaque outil : (1) un schema JSON pour le function-calling, (2) une fonction d'exécution.
"""

import os
import re
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

from .logger import log

DANGEROUS_PATTERNS = (
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){:|:&};:", ":(){",
    "chmod -R 777 /", "sudo rm -rf", "> /dev/sda", "mv /* ", "chown -R root /",
    "wipefs", "shutdown", "reboot", "init 0", "> /dev/null 2>&1 &",
)

MAX_OUTPUT_CHARS = 12000


def is_dangerous(command: str) -> bool:
    cmd = command.strip().lower()
    return any(p in cmd for p in DANGEROUS_PATTERNS)


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    half = MAX_OUTPUT_CHARS // 2
    return (
        text[:half]
        + f"\n\n… [tronqué — {len(text) - MAX_OUTPUT_CHARS} caractères omis] …\n\n"
        + text[-half:]
    )


class ToolRunner:
    """Garde l'état (cwd) entre les appels, comme un vrai shell persistant."""

    def __init__(self, cfg: dict, confirm_callback=None):
        self.cfg = cfg
        self.cwd = os.getcwd()
        self.confirm_callback = confirm_callback or (lambda msg: input(msg).strip().lower() in ("o", "oui", "y", "yes"))

    # ── bash ────────────────────────────────────────────────────────────────
    def bash(self, command: str) -> str:
        log.info(f"bash: {command}")
        if is_dangerous(command) and self.cfg.get("confirm_dangerous", True):
            ok = self.confirm_callback(f"⚠ Commande potentiellement destructrice :\n  {command}\nConfirmer ? [o/N] ")
            if not ok:
                return "Commande annulée par l'utilisateur."

        cd_match = re.match(r'^\s*cd\s*(.*?)\s*$', command)
        if cd_match:
            target = cd_match.group(1).strip().strip("'\"") or str(Path.home())
            try:
                new_path = Path(target).expanduser()
                if not new_path.is_absolute():
                    new_path = Path(self.cwd) / new_path
                new_path = new_path.resolve()
                os.chdir(new_path)
                self.cwd = str(new_path)
                return f"→ {self.cwd}"
            except Exception as e:
                return f"Erreur cd : {e}"

        try:
            wrapped = f"{command} && echo '___CWD___' && pwd"
            r = subprocess.run(
                wrapped, shell=True, capture_output=True, text=True,
                timeout=self.cfg.get("bash_timeout", 60), cwd=self.cwd,
                executable="/bin/bash",
            )
            stdout = r.stdout
            if "___CWD___" in stdout:
                parts, new_cwd = stdout.split("___CWD___")[0], stdout.split("___CWD___")[1].strip()
                output = parts.strip()
                if os.path.isdir(new_cwd):
                    self.cwd = new_cwd
            else:
                output = stdout.strip()
            err = r.stderr.strip()
            out = (output + (("\n" + err) if err else "")).strip()
            out = out if out else "(aucune sortie)"
            return _truncate(out)
        except subprocess.TimeoutExpired:
            return f"Erreur: timeout ({self.cfg.get('bash_timeout', 60)}s)"
        except Exception as e:
            return f"Erreur: {e}"

    # ── fichiers ────────────────────────────────────────────────────────────
    def read_file(self, path: str, start: int = None, end: int = None) -> str:
        try:
            p = self._resolve(path)
            text = p.read_text(encoding="utf-8", errors="replace")
            if start is not None or end is not None:
                lines = text.splitlines()
                s = (start or 1) - 1
                e = end if end is not None else len(lines)
                text = "\n".join(lines[max(s, 0):e])
            return _truncate(text)
        except Exception as e:
            return f"Erreur lecture : {e}"

    def write_file(self, path: str, content: str, mode: str = "overwrite") -> str:
        try:
            p = self._resolve(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            if mode == "append":
                with p.open("a", encoding="utf-8") as f:
                    f.write(content)
            else:
                p.write_text(content, encoding="utf-8")
            return f"✓ Écrit ({len(content)} caractères) → {p}"
        except Exception as e:
            return f"Erreur écriture : {e}"

    def edit_file(self, path: str, old: str, new: str, count: int = 1) -> str:
        try:
            p = self._resolve(path)
            text = p.read_text(encoding="utf-8")
            occurrences = text.count(old)
            if occurrences == 0:
                return f"Erreur : chaîne introuvable dans {p}"
            if count > 0 and occurrences != count:
                return f"Erreur : {occurrences} occurrence(s) trouvée(s), attendu {count}. Précise davantage le contexte."
            text = text.replace(old, new)
            p.write_text(text, encoding="utf-8")
            return f"✓ Remplacé {occurrences} occurrence(s) dans {p}"
        except Exception as e:
            return f"Erreur édition : {e}"

    def list_dir(self, path: str = ".") -> str:
        try:
            p = self._resolve(path)
            entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
            lines = []
            for e in entries:
                tag = "/" if e.is_dir() else ""
                size = "" if e.is_dir() else f" ({e.stat().st_size}o)"
                lines.append(f"{e.name}{tag}{size}")
            return "\n".join(lines) if lines else "(dossier vide)"
        except Exception as e:
            return f"Erreur : {e}"

    def _resolve(self, path: str) -> Path:
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = Path(self.cwd) / p
        return p

    # ── python sandbox (process séparé, pas d'accès direct à l'agent) ───────
    def run_python(self, code: str) -> str:
        log.info("run_python")
        try:
            r = subprocess.run(
                ["python3", "-c", code],
                capture_output=True, text=True, timeout=30, cwd=self.cwd,
            )
            out = (r.stdout + (("\n" + r.stderr) if r.stderr else "")).strip()
            return _truncate(out) if out else "(aucune sortie)"
        except subprocess.TimeoutExpired:
            return "Erreur: timeout (30s)"
        except Exception as e:
            return f"Erreur: {e}"

    # ── git ───────────────────────────────────────────────────────────────
    def git(self, args: str) -> str:
        return self.bash(f"git {args}")

    # ── http (lecture seule, pas d'env réseau arbitraire dangereux) ─────────
    def http_get(self, url: str) -> str:
        log.info(f"http_get: {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "odev-agent/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read(500_000).decode("utf-8", errors="replace")
                return _truncate(data)
        except urllib.error.URLError as e:
            return f"Erreur réseau : {e}"
        except Exception as e:
            return f"Erreur : {e}"


# ── Schémas JSON exposés au modèle ──────────────────────────────────────────
NATIVE_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Exécute une commande shell. Gère fichiers, paquets, réseau, processus, compilation, tests.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Commande bash exacte."}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lit le contenu d'un fichier texte, en entier ou par plage de lignes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start": {"type": "integer", "description": "Ligne de début (1-indexée), optionnel."},
                    "end": {"type": "integer", "description": "Ligne de fin, optionnel."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Écrit ou ajoute du contenu dans un fichier (le crée si besoin).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "mode": {"type": "string", "enum": ["overwrite", "append"], "default": "overwrite"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Remplace une chaîne exacte (old) par une autre (new) dans un fichier existant. Utilise ceci plutôt que de réécrire tout le fichier pour des modifications ciblées.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string", "description": "Texte exact à remplacer."},
                    "new": {"type": "string", "description": "Texte de remplacement."},
                    "count": {"type": "integer", "description": "Nombre d'occurrences attendu (0 = ignorer la vérification).", "default": 1},
                },
                "required": ["path", "old", "new"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "Liste le contenu d'un dossier avec tailles.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "default": "."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Exécute un script Python dans un sous-processus isolé (30s max) et retourne stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Code Python complet à exécuter."}},
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git",
            "description": "Exécute une sous-commande git (status, diff, log, add, commit, branch, etc.) dans le dossier courant.",
            "parameters": {
                "type": "object",
                "properties": {"args": {"type": "string", "description": "Arguments git, ex: 'status -s' ou 'commit -m \"msg\"'."}},
                "required": ["args"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "http_get",
            "description": "Récupère le contenu brut d'une URL (GET uniquement, lecture seule, 500Ko max).",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
]

NATIVE_TOOL_NAMES = {t["function"]["name"] for t in NATIVE_TOOL_SCHEMAS}
