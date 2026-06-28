"""Skill odev: guide TDD pour cadrer une fonctionnalité."""


def get_description():
    return "Produit un plan TDD concret avec scénarios, assertions et fichiers de test probables."


def get_schema():
    return {
        "feature": {"type": "string", "description": "Fonctionnalité à implémenter."},
        "path": {"type": "string", "default": "."},
    }


def run(ctx, args=None):
    args = args or {}
    feature = (args.get("feature") or "la fonctionnalité").strip()
    path = (args.get("path") or ".").strip()
    return "\n".join([
        f"Fonctionnalité: {feature}",
        f"Base de travail: {path}",
        "",
        "Plan TDD:",
        "1. Écris d'abord les tests qui décrivent le comportement attendu.",
        "2. Implémente le minimum pour faire passer le test rouge.",
        "3. Refactorise sans changer les assertions.",
        "",
        "Cas à couvrir:",
        "- Entrée valide principale",
        "- Entrées invalides ou manquantes",
        "- Cas limites et erreurs métier",
        "",
        "Fichiers de test probables:",
        "- `tests/test_<feature>.py`",
        "- `tests/test_<module>_errors.py` si les erreurs sont significatives",
    ])
