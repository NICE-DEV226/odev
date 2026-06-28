"""Skill odev: revue de code approfondie sur un diff ou fichier."""

import subprocess
from pathlib import Path


def get_description():
    return "Effectue une revue de code structurée avec focus correctness, tests, lisibilité et risques."


def get_schema():
    return {
        "path": {"type": "string", "default": "."},
        "diff": {"type": "string", "description": "Diff unifié à analyser, si déjà disponible."},
        "focus": {"type": "string", "default": "correctness"},
    }


def _load_diff(path: Path) -> str:
    root = path if path.is_dir() else path.parent
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


def run(ctx, args=None):
    args = args or {}
    path = Path(args.get("path", ".")).expanduser()
    diff = (args.get("diff") or "").strip() or _load_diff(path)
    focus = (args.get("focus") or "correctness").strip()

    if not diff and path.exists() and path.is_file():
        diff = path.read_text(encoding="utf-8", errors="replace")

    if not diff:
        return "Aucun diff ni fichier exploitable trouvé."

    findings = []
    for raw_line in diff.splitlines():
        if not raw_line.startswith(("+", "-", " ")):
            continue
        line = raw_line.lower()
        if "except exception" in line or "bare except" in line:
            findings.append("- [high] Capture d'exception trop large.")
        elif "todo" in line or "fixme" in line:
            findings.append("- [medium] TODO/FIXME à traiter avant merge.")
        elif "pass" == line.strip():
            findings.append("- [high] Bloc placeholder laissé en place.")
        elif "print(" in line and "logger" not in line:
            findings.append("- [low] Trace de debug potentiellement à retirer.")
        elif "return true" in line or "return false" in line:
            findings.append("- [medium] Vérifier les cas limites autour du booléen.")

    unique_findings = []
    for item in findings:
        if item not in unique_findings:
            unique_findings.append(item)

    return "\n".join([
        f"Contexte: {path}",
        f"Focus: {focus}",
        "",
        "Axes de revue:",
        "- Correctness et cas limites",
        "- Risques de régression",
        "- Couverture de tests",
        "- Lisibilité et dette technique",
        "",
        "Constats:",
        *(unique_findings[:12] if unique_findings else ["- Aucun signal fort détecté automatiquement."]),
        "",
        "Suite recommandée:",
        "- Vérifier les chemins d'erreur.",
        "- Ajouter ou ajuster les tests liés.",
        "- Relire les interfaces publiques modifiées.",
    ])
