"""Skill odev: revue de code approfondie sur un diff, fichier ou dossier."""

import re
from pathlib import Path


def get_description():
    return "Effectue une revue de code structurée avec focus correctness, tests, lisibilité et risques."


def get_schema():
    return {
        "path": {"type": "string", "default": ".", "description": "Chemin du fichier ou dossier à analyser."},
        "diff": {"type": "string", "description": "Diff unifié à analyser, si déjà disponible."},
        "focus": {"type": "string", "default": "correctness"},
    }


PATTERNS = [
    (r"except\s+(Exception|\w+Error)\s*:", "high", "Capture d'exception trop large"),
    (r"except\s*:", "high", "Bare except — attrape tout"),
    (r"\btodo\b", "medium", "TODO à traiter"),
    (r"\bfixme\b", "high", "FIXME à traiter avant merge"),
    (r"^\s*pass\s*$", "high", "Bloc placeholder (pass)"),
    (r"print\s*\(", "low", "Trace de debug (print)"),
    (r"return\s+(True|False)\s*$", "medium", "Booléen en dur — vérifier les cas limites"),
    (r"\.get\(\s*['\"][^'\"]+['\"]\s*\)\s*$", "medium", "Appel .get() sans valeur par défaut"),
    (r"#\s*type:\s*ignore", "medium", "Commentaire type:ignore — vérifier si nécessaire"),
    (r"\bassert\s+False\b", "high", "assert False dans le code (debug ou inachevé)"),
]


def _score_line(line: str):
    for pattern, severity, message in PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return (severity, message)
    return None



def _should_skip(rel: Path) -> bool:
    skip_dirs = {".venv", "venv", "node_modules", "__pycache__", ".git", ".eggs", "dist", "build"}
    return any(p in skip_dirs for p in rel.parts)


def _scan_file(filepath: Path) -> list:
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return [f"- ⚠ Impossible de lire {filepath.name}"]
    findings = []
    for i, line in enumerate(text.splitlines(), 1):
        finding = _score_line(line)
        if finding:
            severity, message = finding
            findings.append(f"- [{severity}] Ligne {i} : {message} : {line.strip()[:100]}")
    return findings


def run(ctx, args=None):
    args = args or {}
    path = Path(args.get("path", ".")).expanduser()
    diff_arg = (args.get("diff") or "").strip()
    focus = (args.get("focus") or "correctness").strip()

    if diff_arg:
        findings = []
        for raw_line in diff_arg.splitlines():
            if not raw_line.startswith(("+", "-", " ")):
                continue
            finding = _score_line(raw_line)
            if finding:
                severity, message = finding
                findings.append(f"- [{severity}] {message} : {raw_line[:140]}")
        unique = []
        for item in findings:
            if item not in unique:
                unique.append(item)
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
            "Constats (diff):",
            *(unique[:15] if unique else ["- Aucun signal détecté dans le diff."]),
            "",
            "Suite recommandée:",
            "- Vérifier les chemins d'erreur.",
            "- Ajouter ou ajuster les tests liés.",
            "- Relire les interfaces publiques modifiées.",
        ])

    if path.exists() and path.is_file():
        if path.suffix == ".py":
            findings = _scan_file(path)
            lines = [
                f"Fichier: {path}",
                f"Focus: {focus}",
                "",
                "Axes de revue:",
                "- Correctness et cas limites",
                "- Risques de régression",
                "- Couverture de tests",
                "- Lisibilité et dette technique",
                "",
            ]
            if findings:
                lines.append("Constats:")
                lines.extend(findings[:20])
            else:
                lines.append("Aucun signal problématique détecté.")
            return "\n".join(lines)
        return f"Extension non supportée: {path.suffix}"

    if path.exists() and path.is_dir():
        py_files = sorted(p for p in path.rglob("*.py") if not _should_skip(p.relative_to(path)))
        if not py_files:
            return "Aucun fichier Python trouvé dans ce dossier."
        lines = [
            f"Dossier analysé: {path}",
            f"Fichiers Python: {len(py_files)}",
            f"Focus: {focus}",
            "",
        ]
        total = 0
        for py in py_files:
            rel = py.relative_to(path)
            findings = _scan_file(py)
            if findings:
                total += len(findings)
                lines.append(f"--- {rel} ---")
                lines.extend(findings)
                lines.append("")
        if total == 0:
            lines.append("Aucun signal problématique détecté dans les fichiers analysés.")
        return "\n".join(lines)

    return f"Le chemin {path} n'existe pas."
