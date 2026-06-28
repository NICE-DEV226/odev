"""Skill odev: triage rapide d'une CI cassée."""


def get_description():
    return "Analyse un log de CI et propose les causes probables, l'ordre d'investigation et les corrections courantes."


def get_schema():
    return {
        "log": {"type": "string", "description": "Extrait de log CI ou message d'échec."},
        "job": {"type": "string", "default": "unknown"},
    }


def run(ctx, args=None):
    args = args or {}
    log_text = (args.get("log") or "").strip()
    job = (args.get("job") or "unknown").strip()

    if not log_text:
        return "Colle le log CI ou le message d'erreur à analyser."

    lowered = log_text.lower()
    causes = []
    if "syntaxerror" in lowered or "indentationerror" in lowered:
        causes.append("- Erreur de syntaxe ou indentation.")
    if "module not found" in lowered or "importerror" in lowered:
        causes.append("- Dépendance manquante ou mauvais packaging.")
    if "failed" in lowered and "test" in lowered:
        causes.append("- Test de non-régression ou assertion cassée.")
    if "permission denied" in lowered:
        causes.append("- Problème de droits ou d'accès à un secret/fichier.")
    if "timeout" in lowered:
        causes.append("- Étape trop lente ou deadlock.")
    if not causes:
        causes.append("- Cause probable dans les dépendances, les tests ou le packaging.")

    return "\n".join([
        f"Job: {job}",
        "",
        "Causes probables:",
        *causes,
        "",
        "Ordre d'investigation:",
        "1. Lire la première erreur réelle dans le log.",
        "2. Reproduire localement avec la commande exacte du job.",
        "3. Vérifier les fichiers touchés récemment et les dépendances.",
        "",
        "Actions rapides:",
        "- Stabiliser les imports et le packaging.",
        "- Réduire le log à l'erreur racine.",
        "- Ajouter un test ciblé si la CI casse sur un comportement.",
    ])
