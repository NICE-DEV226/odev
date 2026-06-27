# Repository Guidelines

## Project Structure & Module Organization
This repository is a small Python package for the `odev` CLI. The main package lives in `odev/`, with the entry script in `odev_main.py`. Core responsibilities are split by module: `cli.py` for command handling, `agent.py` for model/tool orchestration, `tools.py` for native tools, `sessions.py` for session persistence, `config.py` for runtime settings, and `ui.py` for Rich-based terminal output. Keep new modules focused and place shared logic inside `odev/` rather than in the top-level script.

## Build, Test, and Development Commands
- `pip install -e .` installs the package in editable mode and exposes the `odev` command.
- `python3 odev_main.py` starts the CLI without installing it first.
- `odev` launches the interactive session after installation.
- `odev --resume` restores the last saved session.

No dedicated build or test runner is defined in the repository yet. If you add tests, place them under `tests/` and run them with `pytest`.

## Coding Style & Naming Conventions
Use Python 3.9+ syntax, 4-space indentation, and `snake_case` for functions, methods, and modules. Reserve `PascalCase` for classes such as `Agent`. Keep functions small and explicit, prefer type hints on public APIs, and favor short docstrings for module-level intent. Follow the existing French CLI phrasing and keep user-facing messages concise. When formatting changes are needed, use standard Python tooling such as `black` and `isort`.

## Testing Guidelines
The repo currently ships without automated tests. When adding coverage, name files `test_*.py` and keep test cases close to the behavior they exercise. Mock Ollama, filesystem, and shell interactions where possible so tests stay deterministic. For CLI behavior, assert on the returned text or rendered output instead of the internal implementation.

## Commit & Pull Request Guidelines
No local Git history is available in this checkout, so there is no project-specific commit pattern to inherit. Use short, imperative commit subjects such as `fix session loading` or `add tool timeout`. Pull requests should explain the user-facing change, list the commands you ran, and include screenshots or terminal transcripts when behavior or output changes.

## Security & Configuration Tips
Treat `~/.config/odev/config.json` and `~/.config/odev/skills/` as user-specific state. Do not commit local config, API keys, or destructive shell outputs. Review any change to dangerous-command handling carefully, since `odev` can execute shell, Git, and HTTP operations directly.
