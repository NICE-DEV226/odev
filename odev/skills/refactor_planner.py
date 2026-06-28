"""Skill odev: plan de refactor incrémental."""


def get_description():
    return "Propose un refactor incrémental avec ordre de passage, risques et garde-fous."


def get_schema():
    return {
        "subject": {"type": "string", "description": "Module, classe ou zone à refactorer."},
        "goal": {"type": "string", "default": "améliorer la lisibilité et réduire le couplage"},
    }


def run(ctx, args=None):
    args = args or {}
    subject = (args.get("subject") or "la zone concernée").strip()
    goal = (args.get("goal") or "améliorer la lisibilité et réduire le couplage").strip()
    return "\n".join([
        f"Sujet: {subject}",
        f"Objectif: {goal}",
        "",
        "Plan:",
        "1. Extraire les responsabilités indépendantes.",
        "2. Introduire des tests de non-régression avant les changements structurels.",
        "3. Déplacer le code par petits pas vérifiables.",
        "4. Nettoyer les noms, les interfaces et les doublons.",
        "",
        "Garde-fous:",
        "- Ne change qu'une responsabilité à la fois.",
        "- Vérifie chaque étape avec les tests ciblés.",
        "- Préserve le comportement public jusqu'à la fin.",
    ])
