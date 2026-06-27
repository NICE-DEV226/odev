# odev v2 — agent système & code local

Agent CLI complet propulsé par Ollama : exécution shell, manipulation de fichiers,
Python sandboxé, git, requêtes HTTP, skills dynamiques, sessions persistantes.

## Installation

```bash
cd odev_project
pip install -e .          # installe la commande `odev`
# ou, sans installation :
python3 odev_main.py
```

Assure-toi qu'Ollama tourne (`ollama serve`) et qu'un modèle supportant le
function calling est tiré (`ollama pull qwen2.5-coder:7b`).

## Usage

```bash
odev                          # session interactive
odev "résume ce projet"       # message direct
odev --model llama3.1:8b
odev --resume                 # reprend la dernière session
```

## Outils natifs exposés au modèle

| Outil       | Rôle                                              |
|-------------|----------------------------------------------------|
| `bash`      | Exécute n'importe quelle commande shell           |
| `read_file` | Lit un fichier (entier ou par plage de lignes)    |
| `write_file`| Écrit / ajoute dans un fichier                    |
| `edit_file` | Remplacement ciblé d'une chaîne dans un fichier   |
| `list_dir`  | Liste un dossier avec tailles                     |
| `run_python`| Exécute du Python isolé (30s max)                 |
| `git`       | Sous-commandes git                                |
| `http_get`  | Lecture brute d'une URL (lecture seule, 500Ko max)|

## Skills

Dossier : `~/.config/odev/skills/`. Un skill est un fichier `.py` exposant :

```python
def get_description() -> str: ...
def get_schema() -> dict: ...      # optionnel — propriétés JSON des arguments
def run(ctx, args: dict) -> str: ...
```

`/reload` recharge les skills à chaud. Trois skills d'exemple sont créés
automatiquement : `sys_info`, `search_pattern`, `project_summary`.

## Commandes slash

`/help` liste toutes les commandes : changement de modèle, gestion des
sessions (`/save`, `/load`, `/sessions`), configuration (`/config`, `/set`),
skills (`/skills`, `/reload`), navigation (`/cd`), etc.

## Configuration

`~/.config/odev/config.json` — modifiable à chaud via `/set <clé> <valeur>`.
Paramètres notables : `model`, `ollama_host`, `max_loops`, `num_ctx`,
`temperature`, `bash_timeout`, `confirm_dangerous`, `auto_save_session`.

## Sécurité

Les commandes shell jugées destructrices (`rm -rf /`, `mkfs`, fork bombs,
etc.) déclenchent une confirmation interactive avant exécution
(désactivable via `/set confirm_dangerous false`).
