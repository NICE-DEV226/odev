"""Skill odev: revue d'API locale."""


def get_description():
    return "Relit une API ou un endpoint et renvoie les points à vérifier avant livraison."


def get_schema():
    return {
        "endpoint": {"type": "string", "description": "Endpoint, route ou ressource à revoir."},
        "focus": {"type": "string", "default": "stability"},
    }


def run(ctx, args=None):
    args = args or {}
    endpoint = (args.get("endpoint") or "l'API").strip()
    focus = (args.get("focus") or "stability").strip()
    return "\n".join([
        f"Endpoint/API: {endpoint}",
        f"Focus: {focus}",
        "",
        "À vérifier:",
        "- Contrat d'entrée et de sortie stable",
        "- Gestion des erreurs et des statuts",
        "- Authentification/autorisation si nécessaire",
        "- Pagination, filtres et limites si la ressource grossit",
        "- Compatibilité avec les clients existants",
        "",
        "Tests suggérés:",
        "- Succès nominal",
        "- Validation des paramètres",
        "- Cas non autorisé / non trouvé / erreur serveur",
    ])
