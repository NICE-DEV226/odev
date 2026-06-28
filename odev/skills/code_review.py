"""Skill odev: revue de code locale sur diff ou fichier."""

import subprocess
from pathlib import Path


def get_description():
    return "Analyse un diff ou un fichier et renvoie des points de revue classés par priorité."


def get_schema():
    return {
        "path": {"type": "string", "default": "."},
        "diff": {"type": "string", "description": "Diff unifié à analyser, si déjà disponible."},
        "focus": {"type": "string", "default": "correctness"},
    }


def _git_diff(base: Path) -> str:
    root = base if base.is_dir() else base.parent
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "diff", "--no-ext-diff", "--unified=3"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _score_line(line: str):
    lowered = line.lower()
    if "todo" in lowered or "fixme" in lowered:
        return ("medium", "Marqueur TODO/FIXME détecté")
    if "except exception" in lowered:
        return ("high", "Capture trop large d'exception")
    if "pass" == lowered.strip():
        return ("high", "Bloc placeholder laissé en place")
    if "print(" in lowered and "logger" not in lowered:
        return ("low", "Trace de debug potentiellement à retirer")
    if "return true" in lowered or "return false" in lowered:
        return ("medium", "Retour booléen à vérifier pour les cas limites")
    return None


def run(ctx, args=None):
    args = args or {}
    diff = (args.get("diff") or "").strip()
    path = Path(args.get("path", ".")).expanduser()
    focus = (args.get("focus") or "correctness").strip()

    if not diff:
        diff = _git_diff(path)

    if not diff and path.exists() and path.is_file():
        diff = path.read_text(encoding="utf-8", errors="replace")

    if not diff:
        return "Aucun diff ni fichier exploitable trouvé."

    findings = []
    for line in diff.splitlines():
        if not line.startswith(("+", "-", " ")):
            continue
        finding = _score_line(line)
        if finding:
            severity, message = finding
            findings.append(f"- [{severity}] {message} : {line[:140]}")

    header = [
        f"Contexte: {path}",
        f"Focus: {focus}",
        "",
        "Résumé:",
        "- Vérifie les erreurs fonctionnelles, les cas limites et les tests manquants.",
    ]
    if findings:
        header.extend(["", "Points de revue:"] + findings[:12])
    else:
        header.extend(["", "Points de revue:", "- Aucun signal fort détecté automatiquement. Vérifie la logique métier et les tests associés."])

    header.extend([
        "",
        "Tests suggérés:",
        "- Cas nominal",
        "- Cas d'erreur",
        "- Régression sur les chemins modifiés",
    ])
    return "\n".join(header)
