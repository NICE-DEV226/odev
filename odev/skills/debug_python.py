"""Skill odev: debug Python à partir d'un symptôme ou d'un extrait de code."""


def get_description():
    return "Aide à isoler une erreur Python, proposer des hypothèses et un plan de reproduction."


def get_schema():
    return {
        "error": {"type": "string", "description": "Message d'erreur, stack trace ou symptôme."},
        "code": {"type": "string", "description": "Extrait de code concerné.", "default": ""},
        "context": {"type": "string", "default": "."},
    }


def run(ctx, args=None):
    args = args or {}
    error = (args.get("error") or "").strip()
    code = (args.get("code") or "").strip()
    context = (args.get("context") or ".").strip()

    if not error and not code:
        return "Donne une stack trace, un message d'erreur ou un extrait de code à analyser."

    hints = []
    lowered = f"{error}\n{code}".lower()
    if "nameerror" in lowered:
        hints.append("- Vérifie une variable ou fonction non importée / mal nommée.")
    if "importerror" in lowered or "modulenotfounderror" in lowered:
        hints.append("- Vérifie les dépendances, le chemin d'import et l'environnement virtuel.")
    if "typeerror" in lowered:
        hints.append("- Vérifie les types d'entrées et les valeurs `None` inattendues.")
    if "keyerror" in lowered or "indexerror" in lowered:
        hints.append("- Vérifie les accès à dictionnaire / liste avant l'indexation.")
    if "attributeerror" in lowered:
        hints.append("- Vérifie l'objet réel reçu et l'API disponible.")
    if not hints:
        hints.append("- Reproduis avec le plus petit cas possible et observe la première ligne fautive.")

    return "\n".join([
        f"Contexte: {context}",
        "",
        "Symptôme:",
        f"- {error or 'aucun message explicite'}",
        "",
        "Lecture rapide:",
        *hints,
        "",
        "Plan d'action:",
        "1. Reproduire l'erreur avec un script minimal.",
        "2. Isoler l'entrée fautive et les hypothèses implicites.",
        "3. Ajouter un test de non-régression avant le correctif.",
    ])
