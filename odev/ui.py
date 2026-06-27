"""
odev.ui — Rendu terminal via Rich : thème, bannière, affichage texte/outils.
"""

from pathlib import Path
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

THEME = Theme({
    "agent":   "bold cyan",
    "user":    "bold blue",
    "tool":    "bold magenta",
    "result":  "white",
    "warn":    "bold yellow",
    "error":   "bold red",
    "success": "bold green",
    "dim":     "dim white",
})

console = Console(theme=THEME, highlight=False)

MAX_PREVIEW_LINES = 30


def banner(model: str, skills: list, cwd: str, version: str = "2.0"):
    console.clear()
    console.print()
    skills_line = f"  [dim]skills [/dim] {', '.join(skills) if skills else 'aucun'}\n" if skills else ""
    console.print(Panel(
        f"[agent]odev[/agent] v{version}  [dim]agent système & code — local, sans cloud[/dim]\n\n"
        f"  [dim]modèle [/dim] {model}\n"
        f"  [dim]dossier[/dim] {cwd}\n"
        f"{skills_line}"
        f"  [dim]/help pour les commandes[/dim]",
        border_style="cyan", padding=(0, 2),
    ))
    console.print()


def show_user_prompt(cwd: str) -> str:
    console.print(f"[dim]{cwd}[/dim] ", end="")
    return console.input("[user]vous[/user]  ")


def show_thought(thought: str):
    preview = thought[:240] + ("…" if len(thought) > 240 else "")
    console.print(f"\n[dim]  💭 {preview}[/dim]")


def show_text(text: str):
    if not text.strip():
        return
    console.print()
    console.print("[agent]odev[/agent]")
    try:
        console.print(Markdown(text))
    except Exception:
        console.print(text)


def show_tool_start(name: str, args: dict):
    if name == "bash":
        console.print(f"\n  [tool]$[/tool] [dim]{args.get('command', '')}[/dim]")
    elif name == "write_file":
        console.print(f"\n  [tool]✎ write_file[/tool] [dim]{args.get('path', '')}[/dim]")
    elif name == "edit_file":
        console.print(f"\n  [tool]✎ edit_file[/tool] [dim]{args.get('path', '')}[/dim]")
    elif name == "read_file":
        console.print(f"\n  [tool]👁 read_file[/tool] [dim]{args.get('path', '')}[/dim]")
    elif name == "list_dir":
        console.print(f"\n  [tool]📁 list_dir[/tool] [dim]{args.get('path', '.')}[/dim]")
    elif name == "run_python":
        console.print(f"\n  [tool]🐍 run_python[/tool]")
    elif name == "git":
        console.print(f"\n  [tool]⎇ git[/tool] [dim]{args.get('args', '')}[/dim]")
    elif name == "http_get":
        console.print(f"\n  [tool]🌐 http_get[/tool] [dim]{args.get('url', '')}[/dim]")
    elif name.startswith("skill_"):
        console.print(f"\n  [tool]⚙ {name}[/tool] [dim]{args}[/dim]")
    else:
        console.print(f"\n  [tool]⚙ {name}[/tool] [dim]{args}[/dim]")


def show_tool_result(name: str, result: str, full: bool = False):
    if full or name == "read_file":
        console.print(f"[result]{result}[/result]")
        return
    lines = result.split("\n")
    preview = "\n".join(lines[:MAX_PREVIEW_LINES])
    if len(lines) > MAX_PREVIEW_LINES:
        preview += f"\n[dim]… ({len(lines) - MAX_PREVIEW_LINES} lignes supplémentaires)[/dim]"
    console.print(f"[result]{preview}[/result]")


def show_skills_table(registry: dict):
    if not registry:
        console.print("[dim]Aucun skill chargé.[/dim]")
        return
    table = Table(border_style="dim", show_header=True, header_style="bold")
    table.add_column("Skill")
    table.add_column("Description")
    table.add_column("Fichier", style="dim")
    for name, data in registry.items():
        table.add_row(name, data["description"], str(data["file"].name))
    console.print(table)


def show_sessions_table(sessions: list):
    if not sessions:
        console.print("[dim]Aucune session sauvegardée.[/dim]")
        return
    table = Table(border_style="dim", show_header=True, header_style="bold")
    table.add_column("Nom")
    table.add_column("Modèle")
    table.add_column("Messages")
    table.add_column("Mise à jour", style="dim")
    for s in sessions:
        table.add_row(s["name"], s["model"], str(s["n_messages"]), s["updated"])
    console.print(table)


def help_panel(skills_dir: Path):
    console.print(Panel(
        "[dim]/model <nom>[/dim]      changer de modèle (réinitialise l'historique)\n"
        "[dim]/models[/dim]           lister les modèles Ollama disponibles\n"
        "[dim]/skills[/dim]           lister les skills actifs\n"
        "[dim]/reload[/dim]           recharger les skills depuis le disque\n"
        "[dim]/save [nom][/dim]       sauvegarder la session courante\n"
        "[dim]/load <nom>[/dim]       charger une session sauvegardée\n"
        "[dim]/sessions[/dim]         lister les sessions sauvegardées\n"
        "[dim]/clear[/dim]            vider l'historique courant\n"
        "[dim]/cd <path>[/dim]        changer de dossier\n"
        "[dim]/config[/dim]           afficher la configuration courante\n"
        "[dim]/set <clé> <val>[/dim]  modifier un paramètre de configuration\n"
        "[dim]/exit[/dim]             quitter\n\n"
        f"[dim]Skills dir : {skills_dir}[/dim]",
        title="[agent]odev — aide[/agent]",
        border_style="dim", padding=(0, 2),
    ))