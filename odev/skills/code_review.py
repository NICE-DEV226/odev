"""Skill odev: revue de code locale sur diff, fichier ou dossier."""

import re
from pathlib import Path


def get_description():
    return "Analyse un diff, fichier ou dossier et renvoie des points de revue classés par priorité."


def get_schema():
    return {
        "path": {"type": "string", "default": ".", "description": "Chemin du fichier ou dossier à analyser."},
        "diff": {"type": "string", "description": "Diff unifié à analyser, si déjà disponible."},
        "focus": {"type": "string", "default": "correctness"},
    }


PATTERNS = [
    ("high", r"\btodo\b|\bfixme\b", "Marqueur TODO/FIXME laissé dans le code"),
    ("high", r"except\s+Exception", "Capture d'exception trop large (Exception nue)"),
    ("high", r"\bbare\s+except\b", "Bare except sans type d'exception"),
    ("high", r"^\s*pass\s*$", "Bloc placeholder (pass) laissé en place"),
    ("low", r"print\s*\(", "Trace de debug (print) potentiellement à retirer"),
    ("medium", r"return\s+(True|False)\s*$", "Retour booléen en dur — vérifier les cas limites"),
    ("high", r"#\s*FIXME", "FIXME à traiter avant merge"),
    ("medium", r"\.\s*get\(\s*['\"][^'\"]+['\"]\s*\)\s*$", "Appel .get() sans valeur par défaut — peut retourner None"),
    ("low", r"except\s*:", "Capture trop large (except sans type)"),
    ("medium", r"#\s*type:\s*ignore", "Commentaire type:ignore — vérifier si toujours nécessaire"),
]


def _score_line(line: str):
    for severity, pattern, message in PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return (severity, message)
    return None


def _scan_file(filepath: Path) -> list:
    """Analyse un fichier Python et retourne les findings."""
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


def _should_skip(rel: Path) -> bool:
    skip_dirs = {".venv", "venv", "node_modules", "__pycache__", ".git", ".eggs", "dist", "build"}
    return any(p in skip_dirs for p in rel.parts)


def _scan_directory(path: Path) -> str:
    """Analyse tous les fichiers Python d'un dossier."""
    py_files = sorted(p for p in path.rglob("*.py") if not _should_skip(p.relative_to(path)))
    if not py_files:
        return "Aucun fichier Python trouvé dans ce dossier."

    lines = [
        f"Dossier analysé: {path}",
        f"Fichiers Python: {len(py_files)}",
        "",
    ]
    total_findings = 0
    for py in py_files:
        rel = py.relative_to(path)
        findings = _scan_file(py)
        if findings:
            total_findings += len(findings)
            lines.append(f"--- {rel} ---")
            lines.extend(findings)
            lines.append("")
    if total_findings == 0:
        lines.append("Aucun signal problématique détecté dans les fichiers analysés.")
    return "\n".join(lines)


def run(ctx, args=None):
    args = args or {}
    diff_arg = (args.get("diff") or "").strip()
    path = Path(args.get("path", ".")).expanduser()
    focus = (args.get("focus") or "correctness").strip()

    if diff_arg:
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
            "Points de revue (diff):",
        ] + (findings[:20] or ["- Aucun signal détecté dans le diff."])

        return "\n".join(header)

    if path.exists() and path.is_file():
        if path.suffix == ".py":
            findings = _scan_file(path)
            header = [
                f"Fichier: {path}",
                f"Lignes: {len(path.read_text(encoding='utf-8', errors='replace').splitlines())}",
                "",
            ]
            if findings:
                header.append("Points de revue:")
                header.extend(findings[:20])
            else:
                header.append("Aucun signal problématique détecté.")
            return "\n".join(header)
        else:
            return f"Extension non supportée: {path.suffix}. Seuls les fichiers Python sont analysés."

    if path.exists() and path.is_dir():
        return _scan_directory(path)

    return f"Le chemin {path} n'existe pas."
