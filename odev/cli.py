#!/usr/bin/env python3
"""
odev — Agent de code et d'administration système local (v2)
Outils natifs étendus · Skills dynamiques · Sessions persistantes · TUI Rich
"""

import os
import re
import sys
import argparse

try:
    import ollama
except ImportError:
    print("Installe les dépendances nécessaires : pip install ollama rich")
    sys.exit(1)

from .config import load_config, save_config, SKILLS_DIR
from .logger import log
from .skills import load_skills, SKILLS_REGISTRY
from .sessions import list_sessions, save_session, load_session, delete_session
from .agent import Agent
from . import ui

SYSTEM_PROMPT = """Tu es odev, un assistant système et de code de haut niveau opérant directement dans le terminal.
Tu es direct, pragmatique et extrêmement efficace. Tu réponds en français sauf si on te demande explicitement une autre langue.

Tu disposes des outils suivants :
- bash(command) : exécute n'importe quelle commande shell.
- read_file / write_file / edit_file / list_dir : manipulation fine de fichiers (préfère edit_file pour des modifications ciblées plutôt que réécrire un fichier entier).
- run_python(code) : exécute du Python isolé pour des calculs ou scripts ponctuels.
- git(args) : sous-commandes git dans le dossier courant.
- http_get(url) : récupère le contenu brut d'une page (lecture seule).
- skill_<nom> : capacités spécialisées chargées dynamiquement, vois /skills.

Règles critiques :
1. Utilise les outils dédiés (read_file, write_file, edit_file) plutôt que bash quand c'est plus précis et plus sûr.
2. Pour une édition ciblée dans un fichier existant, utilise edit_file plutôt que de tout réécrire.
3. Avant une action destructrice ou irréversible, explique brièvement ce que tu vas faire.
4. Reste concis dans tes explications. Pas de longs discours après l'exécution d'un outil.
5. Si une commande échoue, analyse l'erreur et corrige plutôt que de répéter la même commande.
"""

SHELL_BUILTINS = {
    "ls", "ll", "la", "pwd", "cat", "less", "head", "tail", "grep", "find",
    "git", "pip", "pip3", "uv", "npm", "yarn", "cargo", "make", "docker",
    "python", "python3", "node", "bash", "sh", "echo", "touch", "mkdir",
    "cp", "mv", "rm", "chmod", "chown", "ps", "top", "htop", "df", "du",
    "curl", "wget", "ssh", "scp", "tar", "zip", "unzip", "which", "whereis",
    "env", "export", "source", "systemctl", "journalctl", "pacman", "yay",
    "apt", "apt-get", "dnf", "awk", "sed", "sort", "uniq", "wc", "diff",
}


def is_shell_command(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    first_word = stripped.split()[0].lstrip("./")
    return (
        first_word in SHELL_BUILTINS
        or stripped.startswith("./")
        or stripped.startswith("../")
        or (len(stripped.split()) == 1 and "/" in stripped)
        or re.match(r'^[a-z0-9_-]+ +-', stripped) is not None
    )


def check_model(client, model: str) -> str:
    try:
        available = [m.model for m in client.list().models]
    except Exception:
        ui.console.print(f"[error]✗ Impossible de contacter Ollama[/error]")
        sys.exit(1)
    if model not in available:
        ui.console.print(f"[warn]⚠ '{model}' non trouvé[/warn]")
        ui.console.print(f"[dim]Disponibles : {', '.join(available)}[/dim]")
        if available:
            model = available[0]
            ui.console.print(f"[dim]→ fallback sur {model}[/dim]")
        else:
            sys.exit(1)
    return model


def confirm_callback(message: str) -> bool:
    answer = ui.console.input(f"[warn]{message}[/warn]").strip().lower()
    return answer in ("o", "oui", "y", "yes")


def make_agent(client, cfg) -> Agent:
    return Agent(
        client, cfg,
        confirm_callback=confirm_callback,
        on_text=ui.show_text,
        on_tool_start=ui.show_tool_start,
        on_tool_result=ui.show_tool_result,
        on_thought=ui.show_thought,
    )


def handle_slash(cmd: str, model: str, messages: list, client, cfg: dict, current_session: list):
    parts = cmd.strip().split(None, 1)
    action = parts[0].lower()

    if action in ("/exit", "/quit", "/q"):
        if cfg.get("auto_save_session"):
            save_session("_last", model, messages)
        ui.console.print("[dim]À bientôt.[/dim]")
        sys.exit(0)

    elif action == "/clear":
        messages = [messages[0]]
        ui.console.clear()
        ui.console.print("[dim]Historique vidé.[/dim]")

    elif action == "/models":
        try:
            ui.console.print()
            for m in client.list().models:
                mark = "[agent]●[/agent]" if m.model == model else "[dim]○[/dim]"
                size = f"{m.size / 1e9:.1f} Go"
                ui.console.print(f"  {mark} {m.model}  [dim]{size}[/dim]")
            ui.console.print()
        except Exception as e:
            ui.console.print(f"[error]✗ {e}[/error]")

    elif action == "/model":
        if len(parts) < 2:
            ui.console.print(f"[dim]actuel : {model}[/dim]")
        else:
            new_model = check_model(client, parts[1].strip())
            model = new_model
            messages = [messages[0]]
            ui.console.print(f"[dim]→ {model} (historique réinitialisé)[/dim]")

    elif action == "/cd":
        if len(parts) > 1:
            try:
                os.chdir(os.path.expanduser(parts[1]))
                ui.console.print(f"[dim]→ {os.getcwd()}[/dim]")
            except Exception as e:
                ui.console.print(f"[error]✗ {e}[/error]")

    elif action == "/skills":
        ui.show_skills_table(SKILLS_REGISTRY)

    elif action == "/reload":
        loaded, errors = load_skills()
        ui.console.print(f"[dim]Skills chargés : {', '.join(loaded) if loaded else 'aucun'}[/dim]")
        for e in errors:
            ui.console.print(f"[error]✗ {e}[/error]")

    elif action == "/save":
        name = parts[1].strip() if len(parts) > 1 else "default"
        path = save_session(name, model, messages)
        ui.console.print(f"[success]✓ Session sauvegardée : {path}[/success]")

    elif action == "/load":
        if len(parts) < 2:
            ui.console.print("[warn]Usage : /load <nom>[/warn]")
        else:
            result = load_session(parts[1].strip())
            if result is None:
                ui.console.print(f"[error]✗ Session '{parts[1].strip()}' introuvable.[/error]")
            else:
                loaded_model, loaded_messages = result
                model = loaded_model or model
                messages = loaded_messages
                ui.console.print(f"[success]✓ Session chargée ({len(messages)} messages, modèle {model})[/success]")

    elif action == "/sessions":
        ui.show_sessions_table(list_sessions())

    elif action == "/config":
        for k, v in cfg.items():
            ui.console.print(f"  [dim]{k}[/dim] = {v}")

    elif action == "/set":
        if len(parts) < 2 or len(parts[1].split(None, 1)) < 2:
            ui.console.print("[warn]Usage : /set <clé> <valeur>[/warn]")
        else:
            key, val = parts[1].split(None, 1)
            if key not in cfg:
                ui.console.print(f"[warn]Clé inconnue : {key}[/warn]")
            else:
                # Coercition de type basique selon la valeur par défaut existante
                old = cfg[key]
                try:
                    if isinstance(old, bool):
                        cfg[key] = val.strip().lower() in ("1", "true", "o", "oui", "yes")
                    elif isinstance(old, int):
                        cfg[key] = int(val)
                    elif isinstance(old, float):
                        cfg[key] = float(val)
                    else:
                        cfg[key] = val
                    save_config(cfg)
                    ui.console.print(f"[success]✓ {key} = {cfg[key]}[/success]")
                except ValueError:
                    ui.console.print(f"[error]✗ Valeur invalide pour {key}[/error]")

    elif action in ("/help", "/?"):
        ui.help_panel(SKILLS_DIR)

    else:
        ui.console.print(f"[warn]?[/warn] commande inconnue — [dim]/help[/dim]")

    return model, messages


def main():
    parser = argparse.ArgumentParser(description="odev — agent système & code local")
    parser.add_argument("--model", "-m", default=None, help="Modèle Ollama à utiliser")
    parser.add_argument("--host", default=None, help="URL du serveur Ollama")
    parser.add_argument("--resume", action="store_true", help="Reprend la dernière session")
    parser.add_argument("message", nargs="*")
    args = parser.parse_args()

    cfg = load_config()
    if args.model:
        cfg["model"] = args.model
    if args.host:
        cfg["ollama_host"] = args.host

    client = ollama.Client(host=cfg["ollama_host"])
    model = check_model(client, cfg["model"])
    loaded, errors = load_skills()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if args.resume:
        result = load_session("_last")
        if result:
            model, messages = result

    ui.banner(model, loaded, os.getcwd())
    for e in errors:
        ui.console.print(f"[error]✗ skill : {e}[/error]")

    agent = make_agent(client, cfg)

    if args.message:
        msg = " ".join(args.message)
        ui.console.print(f"[user]vous[/user]  {msg}")
        messages.append({"role": "user", "content": msg})
        messages = agent.turn(model, messages)

    while True:
        try:
            inp = ui.show_user_prompt(os.getcwd()).strip()
        except (EOFError, KeyboardInterrupt):
            ui.console.print("\n[dim]À bientôt.[/dim]")
            if cfg.get("auto_save_session"):
                save_session("_last", model, messages)
            break

        if not inp:
            continue

        if inp.startswith("/"):
            model, messages = handle_slash(inp, model, messages, client, cfg, messages)
            agent.cfg = cfg
            agent.runner.cfg = cfg
            continue

        if is_shell_command(inp):
            result = agent.runner.bash(inp)
            ui.show_tool_result("bash", result)
            ui.console.print()
            messages.append({"role": "user", "content": f"$ {inp}"})
            messages.append({"role": "assistant", "content": result})
            continue

        messages.append({"role": "user", "content": inp})
        messages = agent.turn(model, messages)

        if cfg.get("auto_save_session"):
            save_session("_last", model, messages)


if __name__ == "__main__":
    main()
