# AGENTS.md — odev v2

## Quick start

- `pip install -e .` → `odev` command; `python3 odev_main.py` without install.
- Ollama required (`ollama serve` + tool-calling model, default `qwen2.5-coder:7b`).
- `odev --resume` restores `_last.json` session.

## Commands

```
make run/dev   → python3 odev_main.py
make test      → python3 -m unittest discover -s tests -p 'test_*.py'
make check     → python3 -m compileall odev odev_main.py
make clean     → find . -type d -name __pycache__ -prune -exec rm -rf {} +
```

CI: `pip install -e .` → `make test` → `make check`.

## Layout

`odev/cli.py` — argparse, slash commands, shell detection, main loop, `/agent` switcher.  
`odev/agent.py` — Agent class with tool-calling loop, streaming, history trim, repeat guard, fallback parser, **sub-agent delegation**.  
`odev/tools.py` — ToolRunner (persistent cwd): bash, read/write/edit_file, apply_patch, list_dir, run_python, git, http_get, **subagent tool schema**.  
`odev/agents/` — registry of specialized agents (coder, reviewer, explorer, planner) with dedicated system prompts.  
`odev/config.py` — loads `~/.config/odev/config.json` (overridable via `ODEV_HOME`).  
`odev/sessions.py` — persist/load sessions as JSON in `sessions/`.  
`odev/memory.py` — persistent summary/tasks/notes in `memory.json`.  
`odev/skills.py` — dynamic skill loader (bundled `odev/skills/` + user `~/.config/odev/skills/`).  
`odev/ui.py` — Rich TUI: 5 themes (`codex`, `claude`, `gemini`, `nord`, `catppuccin`), syntax highlighting, thinking/subagent panels.  
`odev/logger.py` — rotating file logger → `odev.log`.

Entry: `pyproject.toml` → `odev.cli:main`; `odev_main.py` sets `sys.path`.

## Multi-agent system

`/agent <type>` switches the model's persona. Available types:

| Type | Role |
|---|---|
| `auto` | Choix automatique selon la tâche (défaut) |
| `coder` | Écriture et débogage de code |
| `reviewer` | Revue de code et analyse qualité |
| `explorer` | Exploration et compréhension de codebase (lecture seule) |
| `planner` | Planification de tâches complexes |

Agents can delegate to each other recursively via the **`subagent`** tool:
- `subagent("explorer", "trouve les points d'entrée", context="...")` → explore la base
- `subagent("reviewer", "revise ce fichier")` → analyse qualité
- `subagent("planner", "planifie cette feature")` → décompose en étapes

Each sub-agent runs in isolation with its own specialized system prompt, then returns results to the caller. Default depth limit prevents infinite recursion (`max_loops` capped at 12 for sub-agents).

## Testing quirks

- Tests **must** use `import_with_temp_home()` which sets `ODEV_HOME` to a temp dir and re-imports `odev.*` modules — do not break this isolation.
- `test_apply_patch` requires `patch` on `$PATH`.
- Dependencies: `ollama>=0.4.0`, `rich>=13.0.0`, `pygments>=2.15.0` (uv.lock present, pip also works).

## Non-obvious behavior

- `cd` in bash tool is **intercepted** by ToolRunner (not run via subprocess). `cd` into a non-existent dir returns an error string, does not throw.
- Raw shell commands typed at the CLI prompt (matched against `SHELL_BUILTINS` in `cli.py:61`) **skip the agent entirely** and run directly via ToolRunner.
- `run_python` uses `python3 -I -S` (isolated, no site packages).
- `apply_patch` auto-detects strip level (1 if patch starts with `--- a/`, else 0).
- History trimmed to 60 messages (`max_history_messages`). 3 identical tool calls in a row → loop guard triggered.
- Fallback parser extracts tool calls from ```bash and ```json fences (for small models without native tool-calling).
- `<think>...</think>` blocks are captured and displayed as a thinking panel in the UI. Special tokens (`<|im_start|>`, `<|eot_id|>`) are stripped from output.
- Empty model response → one retry with "reply in plain text" prompt.
- Agent config (`cfg`) is **mutated on the agent object** after every slash command (`cli.py:357-358`).

## Skills

Write a `.py` to `~/.config/odev/skills/` with `get_description()`, optional `get_schema()`, and `run(ctx, args)`.  
Bundled: `odev/skills/` (no `__init__.py` — flat file collection).  
`/reload` hot-reloads from disk.

## Configuration (`/set` or `~/.config/odev/config.json`)

`model`, `ollama_host` (also `OLLAMA_HOST` env), `num_ctx` (16384), `temperature` (0.1), `max_loops` (24), `bash_timeout` (60), `confirm_dangerous`, `auto_save_session`, `ui_style` (codex/claude/gemini/nord/catppuccin).
