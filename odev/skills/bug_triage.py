"""Skill odev: triage rapide d'un bug ou d'une erreur."""


def get_description():
    return "Classe un bug, propose des hypothèses, puis donne un plan d'investigation court."


def get_schema():
    return {
        "symptom": {"type": "string", "description": "Symptôme, stack trace ou message d'erreur."},
        "path": {"type": "string", "default": "."},
    }


def run(ctx, args=None):
    args = args or {}
    symptom = (args.get("symptom") or "").strip()
    path = (args.get("path") or ".").strip()

    if not symptom:
        return "Décris le symptôme ou colle la stack trace, puis relance ce skill."

    lowered = symptom.lower()
    causes = []
    if "timeout" in lowered:
        causes.append("- Temps d'exécution trop long ou appel réseau bloqué.")
    if "traceback" in lowered or "exception" in lowered:
        causes.append("- Exception non gérée ou mauvaise hypothèse sur les entrées.")
    if "not found" in lowered or "introuvable" in lowered:
        causes.append("- Chemin, clé ou dépendance absente.")
    if "permission" in lowered or "denied" in lowered:
        causes.append("- Problème de droits ou d'environnement.")

    if not causes:
        causes.append("- Logique métier invalide ou état inattendu.")

    return "\n".join([
        f"Base de travail: {path}",
        "",
        "Symptôme:",
        f"- {symptom}",
        "",
        "Hypothèses:",
        *causes,
        "",
        "Investigation:",
        "- Reproduire avec un cas minimal.",
        "- Isoler la première ligne fautive.",
        "- Vérifier les changements récents et les tests voisins.",
    ])
