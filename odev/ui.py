"""
odev.ui — Rendu terminal via Rich : markdown colorisé, thèmes complets, panneaux d'outils.
"""

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.theme import Theme
from rich.markup import escape
from rich import box

MAX_PREVIEW_LINES = 30

STYLE_PRESETS = {
    "codex": {
        "agent": "bold cyan",
        "user": "bold bright_cyan",
        "tool": "bold magenta",
        "result": "white",
        "warn": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "dim": "dim white",
        "border": "cyan",
        "tool_border": "bright_black",
        "thought_border": "bright_black",
        "brand": "odev",
        "subtitle": "local code agent",
        "icon": "◆",
        "code_theme": "monokai",
    },
    "claude": {
        "agent": "bold bright_magenta",
        "user": "bold white",
        "tool": "bold bright_red",
        "result": "white",
        "warn": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "dim": "dim white",
        "border": "magenta",
        "tool_border": "red",
        "thought_border": "bright_black",
        "brand": "Claude",
        "subtitle": "clean assistant workspace",
        "icon": "✦",
        "code_theme": "dracula",
    },
    "gemini": {
        "agent": "bold bright_green",
        "user": "bold bright_blue",
        "tool": "bold bright_yellow",
        "result": "white",
        "warn": "bold yellow",
        "error": "bold red",
        "success": "bold green",
        "dim": "dim white",
        "border": "blue",
        "tool_border": "yellow",
        "thought_border": "bright_black",
        "brand": "Gemini",
        "subtitle": "multimodal workspace",
        "icon": "◇",
        "code_theme": "one-dark",
    },
    "nord": {
        "agent": "bold #88C0D0",
        "user": "bold #8FBCBB",
        "tool": "bold #D08770",
        "result": "#ECEFF4",
        "warn": "bold #EBCB8B",
        "error": "bold #BF616A",
        "success": "bold #A3BE8C",
        "dim": "dim #D8DEE9",
        "border": "#81A1C1",
        "tool_border": "#5E81AC",
        "thought_border": "#4C566A",
        "brand": "Nord",
        "subtitle": "arctic terminal",
        "icon": "▸",
        "code_theme": "nord",
    },
    "catppuccin": {
        "agent": "bold #89B4FA",
        "user": "bold #A6E3A1",
        "tool": "bold #F38BA8",
        "result": "#CDD6F4",
        "warn": "bold #F9E2AF",
        "error": "bold #F38BA8",
        "success": "bold #A6E3A1",
        "dim": "dim #6C7086",
        "border": "#89B4FA",
        "tool_border": "#585B70",
        "thought_border": "#45475A",
        "brand": "Catppuccin",
        "subtitle": "mocha terminal",
        "icon": "⋆",
        "code_theme": "catppuccin-frappe",
    },
}

_current_style = "codex"
_preset = STYLE_PRESETS[_current_style]
console = Console(theme=Theme({
    "agent": _preset["agent"],
    "user": _preset["user"],
    "tool": _preset["tool"],
    "result": _preset["result"],
    "warn": _preset["warn"],
    "error": _preset["error"],
    "success": _preset["success"],
    "dim": _preset["dim"],
}), highlight=False)


def available_styles() -> list:
    return sorted(STYLE_PRESETS)


def get_style() -> str:
    return _current_style


def set_style(style: str) -> str:
    global console, _current_style, _preset
    normalized = (style or "codex").strip().lower()
    if normalized not in STYLE_PRESETS:
        normalized = "codex"
    _current_style = normalized
    _preset = STYLE_PRESETS[_current_style]
    console = Console(theme=Theme({
        "agent": _preset["agent"],
        "user": _preset["user"],
        "tool": _preset["tool"],
        "result": _preset["result"],
        "warn": _preset["warn"],
        "error": _preset["error"],
        "success": _preset["success"],
        "dim": _preset["dim"],
    }), highlight=False)
    return _current_style


def _preview(text: str, limit: int = 120) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def banner(model: str, skills: list, cwd: str, version: str = "2.0", memory: Optional[dict] = None, agent_type: str = "auto"):
    console.clear()
    console.print()
    summary = ""
    tasks = 0
    if memory:
        summary = _preview(memory.get("project_summary") or "", 110)
        tasks = len(memory.get("active_tasks", []))

    body = [
        f" {_preset['icon']} [agent]{_preset['brand']}[/agent] v{version}  [dim]{_preset['subtitle']}[/dim]",
        "",
        f"  [dim]theme[/dim]   [success]{_current_style}[/success]",
        f"  [dim]model[/dim]   {model}",
        f"  [dim]agent[/dim]   {agent_type}",
        f"  [dim]cwd[/dim]     {cwd}",
    ]
    if summary:
        body.append(f"  [dim]summary[/dim] {summary}")
    if tasks:
        body.append(f"  [dim]tasks[/dim]   {tasks} active")
    if skills:
        body.append(f"  [dim]skills[/dim]  {', '.join(skills)}")
    body.append("")
    body.append(f"  [dim]{_preset['icon']} /help for commands[/dim]")

    console.print(Panel("\n".join(body), border_style=_preset["border"], padding=(0, 2)))
    console.print()


def show_user_prompt(cwd: str) -> str:
    console.print(f"[dim]{cwd}[/dim] ", end="")
    return console.input(f"[user]{_preset['icon']}[/user]  ")


def show_thought(thought: str):
    preview = thought[:500] + ("…" if len(thought) > 500 else "")
    console.print(Panel(
        f"[dim]{escape(preview)}[/dim]",
        title=f"[dim]{_preset['icon']} réflexion[/dim]",
        border_style=_preset["thought_border"],
        padding=(0, 1),
        width=min(console.width, 100),
    ))


def show_text(text: str):
    if not text.strip():
        return
    console.print()
    console.print(f"[agent]{_preset['icon']} odev[/agent]")
    try:
        md = Markdown(text, code_theme=_preset.get("code_theme", "monokai"))
        console.print(md)
    except Exception:
        console.print(text)


def start_stream():
    console.print()
    console.print(f"[agent]{_preset['icon']} odev[/agent] ", end="")


def stream_token(token: str):
    console.print(token, end="")


def end_stream():
    console.print()


_TOOL_ICONS = {
    "bash": "$",
    "write_file": "✎",
    "edit_file": "✎",
    "apply_patch": "🩹",
    "read_file": "👁",
    "list_dir": "📁",
    "run_python": "🐍",
    "git": "⎇",
    "http_get": "🌐",
}


def show_tool_start(name: str, args: dict):
    if name.startswith("subagent:"):
        agent_type = name[9:]
        task = args.get("task", "")
        console.print(f"\n  [tool]🔄 subagent:[/tool][tool]{agent_type}[/tool] [dim]{task}[/dim]")
        return
    icon = _TOOL_ICONS.get(name, "⚙")
    detail = ""
    if "command" in args:
        detail = args["command"]
    elif "path" in args:
        detail = args["path"]
    elif "args" in args:
        detail = args["args"]
    elif "url" in args:
        detail = args["url"]
    elif name.startswith("skill_"):
        detail = str(args)
    if detail:
        console.print(f"\n  [tool]{icon} {name}[/tool] [dim]{detail}[/dim]")
    else:
        console.print(f"\n  [tool]{icon} {name}[/tool]")


def show_tool_result(name: str, result: str, full: bool = False):
    if name.startswith("subagent:"):
        agent_type = name[9:]
        lines = result.split("\n")
        preview = "\n".join(lines[:MAX_PREVIEW_LINES])
        if len(lines) > MAX_PREVIEW_LINES:
            preview += f"\n[dim]… ({len(lines) - MAX_PREVIEW_LINES} lines more)[/dim]"
        console.print(Panel(
            preview,
            title=f"[tool]subagent:{agent_type}[/tool]",
            border_style=_preset["tool_border"],
            padding=(0, 1),
        ))
        return
    if full or name == "read_file":
        lines = result.split("\n")
        preview = "\n".join(lines[:MAX_PREVIEW_LINES * 2])
        if len(lines) > MAX_PREVIEW_LINES * 2:
            preview += f"\n[dim]… ({len(lines) - MAX_PREVIEW_LINES * 2} lines more)[/dim]"
        console.print(Panel(
            preview,
            title=f"[tool]{name}[/tool]",
            border_style=_preset["tool_border"],
            padding=(0, 1),
        ))
        return
    lines = result.split("\n")
    preview = "\n".join(lines[:MAX_PREVIEW_LINES])
    if len(lines) > MAX_PREVIEW_LINES:
        preview += f"\n[dim]… ({len(lines) - MAX_PREVIEW_LINES} lines more)[/dim]"
    console.print(Panel(
        preview,
        title=f"[tool]{name}[/tool]",
        border_style=_preset["tool_border"],
        padding=(0, 1),
    ))


def show_skills_table(registry: dict):
    if not registry:
        console.print("[dim]Aucun skill chargé.[/dim]")
        return
    table = Table(border_style=_preset["tool_border"], show_header=True, header_style="bold", box=box.SIMPLE)
    table.add_column("Skill")
    table.add_column("Description")
    table.add_column("File", style="dim")
    for name, data in registry.items():
        table.add_row(name, data["description"], str(data["file"].name))
    console.print(table)


def show_sessions_table(sessions: list):
    if not sessions:
        console.print("[dim]Aucune session sauvegardée.[/dim]")
        return
    table = Table(border_style=_preset["tool_border"], show_header=True, header_style="bold", box=box.SIMPLE)
    table.add_column("Name")
    table.add_column("Model")
    table.add_column("Agent")
    table.add_column("Messages")
    table.add_column("Updated", style="dim")
    for s in sessions:
        table.add_row(s["name"], s["model"], s.get("agent_type", "?"), str(s["n_messages"]), s["updated"])
    console.print(table)


def help_panel(skills_dir: Path):
    console.print(Panel(
        f"[dim]{_preset['icon']} /theme <codex|claude|gemini|nord|catppuccin>[/dim]  switch UI style\n"
        f"[dim]{_preset['icon']} /agent <type>[/dim]                changer d'agent spécialisé\n"
        f"[dim]{_preset['icon']} /model <nom>[/dim]                 changer de modèle\n"
        f"[dim]{_preset['icon']} /models[/dim]                      lister les modèles Ollama\n"
        f"[dim]{_preset['icon']} /skills[/dim]                      lister les skills actifs\n"
        f"[dim]{_preset['icon']} /reload[/dim]                      recharger les skills\n"
        f"[dim]{_preset['icon']} /memory[/dim]                      afficher la mémoire\n"
        f"[dim]{_preset['icon']} /summary[/dim]                     résumé projet\n"
        f"[dim]{_preset['icon']} /tasks /task /done[/dim]           gestion des tâches\n"
        f"[dim]{_preset['icon']} /note <texte>[/dim]                ajouter une note\n"
        f"[dim]{_preset['icon']} /save /load /sessions[/dim]        sessions\n"
        f"[dim]{_preset['icon']} /clear[/dim]                       vider l'historique\n"
        f"[dim]{_preset['icon']} /cd <path>[/dim]                   changer de dossier\n"
        f"[dim]{_preset['icon']} /config /set[/dim]                 configuration\n"
        f"[dim]{_preset['icon']} /exit[/dim]                        quitter\n\n"
        f"[dim]Skills : {skills_dir}[/dim]",
        title=f"[agent]{_preset['icon']} odev — {get_style()}[/agent]",
        border_style=_preset["border"],
        padding=(0, 2),
    ))
