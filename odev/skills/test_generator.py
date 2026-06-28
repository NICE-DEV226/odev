"""Skill odev: génération de scénarios de test."""


def get_description():
    return "Propose des tests unitaires et de régression adaptés à une fonctionnalité ou un bug."


def get_schema():
    return {
        "subject": {"type": "string", "description": "Fonctionnalité, bug ou module à tester."},
        "style": {"type": "string", "default": "pytest"},
    }


def run(ctx, args=None):
    args = args or {}
    subject = (args.get("subject") or "la fonctionnalité").strip()
    style = (args.get("style") or "pytest").strip()
    return "\n".join([
        f"Sujet: {subject}",
        f"Style: {style}",
        "",
        "Cas à écrire:",
        "1. Cas nominal avec données valides.",
        "2. Cas d'erreur ou d'entrée invalide.",
        "3. Cas limite ou état absent.",
        "4. Régression sur le bug signalé si applicable.",
        "",
        "Bonnes pratiques:",
        "- Isole les dépendances externes.",
        "- Vérifie les effets de bord, pas seulement les retours.",
        "- Nomme les tests selon le comportement observé.",
        "",
        "Fichiers probables:",
        "- `tests/test_<module>.py`",
        "- `tests/test_<module>_errors.py`",
    ])
