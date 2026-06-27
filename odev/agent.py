"""
odev.agent — Boucle agentique : appelle le modèle, dispatch les tool calls,
gère le streaming, le fallback de parsing, et la compression d'historique.
"""

import re
import json

from .tools import ToolRunner, NATIVE_TOOL_SCHEMAS, NATIVE_TOOL_NAMES
from .skills import skill_tool_schemas, run_skill, SKILLS_REGISTRY
from .logger import log


THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

# Tokens de template de chat qui fuient parfois dans le contenu avec les petits modèles
# (Qwen/ChatML, Llama, etc.) quand le stop n'a pas coupé assez tôt.
SPECIAL_TOKEN_RE = re.compile(
    r"<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|<\|eot_id\|>|<\|start_header_id\|>.*?<\|end_header_id\|>",
    re.DOTALL,
)

STOP_TOKENS = ["<|im_start|>", "<|im_end|>", "<|endoftext|>", "<|eot_id|>"]


def strip_think(text: str):
    """Retire les blocs <think> et les tokens spéciaux résiduels, retourne (texte_propre, pensée_ou_None)."""
    m = THINK_RE.search(text)
    if not m:
        thought, clean = None, text
    else:
        thought = m.group(1).strip()
        clean = THINK_RE.sub("", text).strip()
    clean = SPECIAL_TOKEN_RE.sub("", clean).strip()
    return clean, (thought or None)


def extract_fallback_tool_calls(text: str) -> list:
    """Filet de sécurité quand le modèle ne fait pas de vrai tool-calling natif
    mais émet des blocs ```bash``` ou du JSON pseudo-tool-call dans le texte."""
    results = []

    for m in re.finditer(r'```(?:bash|sh|shell)\s*\n(.*?)\n```', text, re.DOTALL | re.IGNORECASE):
        cmd = m.group(1).strip()
        if cmd:
            results.append(("bash", {"command": cmd}))

    candidates = []
    for m in re.finditer(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL):
        candidates.append(m.group(1).strip())
    if not candidates:
        for m in re.finditer(r'(\{[^{}]*"(?:arguments|parameters)"\s*:\s*\{[^{}]*\}[^{}]*\})', text, re.DOTALL):
            candidates.append(m.group(1).strip())

    for raw in candidates:
        try:
            obj = json.loads(raw)
            name = obj.get("name", "")
            args = obj.get("arguments") or obj.get("parameters") or {}
            if not name:
                continue
            if name in NATIVE_TOOL_NAMES:
                results.append((name, args))
            elif name.startswith("skill_") and name[6:] in SKILLS_REGISTRY:
                results.append((name, args))
            elif "command" in args:
                results.append(("bash", {"command": args["command"]}))
            else:
                # Outil hallucinet par un petit modèle : on le fait quand même
                # passer par dispatch() pour renvoyer un message d'erreur clair
                # plutôt que de laisser le JSON brut s'afficher tel quel.
                results.append((name, args))
        except json.JSONDecodeError:
            continue

    return results


def strip_fallback_blocks(text: str) -> str:
    text = re.sub(r'```(?:json|bash|sh|shell)?\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
    text = re.sub(r'```(?:bash|sh|shell)\s*\n.*?\n```', '', text, flags=re.DOTALL)
    text = re.sub(r'\{[^{}]*"(?:arguments|parameters)"\s*:\s*\{[^{}]*\}[^{}]*\}', '', text, flags=re.DOTALL)
    return text.strip()


def build_tools() -> list:
    return list(NATIVE_TOOL_SCHEMAS) + skill_tool_schemas()


def trim_history(messages: list, max_messages: int) -> list:
    """Garde le system prompt + les N derniers messages pour limiter le contexte."""
    if len(messages) <= max_messages + 1:
        return messages
    system = messages[0]
    tail = messages[-max_messages:]
    # Évite de couper au milieu d'un échange tool sans son message assistant déclencheur
    while tail and tail[0].get("role") == "tool":
        tail.pop(0)
    return [system] + tail


class Agent:
    def __init__(self, client, cfg: dict, confirm_callback=None, on_text=None, on_tool_start=None, on_tool_result=None, on_thought=None):
        self.client = client
        self.cfg = cfg
        self.runner = ToolRunner(cfg, confirm_callback=confirm_callback)
        self.on_text = on_text or (lambda t: None)
        self.on_tool_start = on_tool_start or (lambda kind, payload: None)
        self.on_tool_result = on_tool_result or (lambda kind, result: None)
        self.on_thought = on_thought or (lambda t: None)

    def call_model(self, model: str, messages: list):
        tools = build_tools()
        try:
            resp = self.client.chat(
                model=model,
                messages=messages,
                tools=tools,
                stream=False,
                keep_alive=self.cfg.get("keep_alive", "10m"),
                options={
                    "temperature": self.cfg.get("temperature", 0.1),
                    "num_ctx": self.cfg.get("num_ctx", 16384),
                    "stop": STOP_TOKENS,
                },
            )
        except Exception as e:
            log.error(f"appel modèle échoué: {e}")
            return f"[Erreur Ollama] {e}", []

        msg = resp.message
        raw_text = msg.content or ""
        text, thought = strip_think(raw_text)
        if thought:
            self.on_thought(thought)

        calls = []
        native_calls = list(msg.tool_calls or [])
        if native_calls:
            for tc in native_calls:
                name = tc.function.name
                args = tc.function.arguments or {}
                calls.append((name, args))
        else:
            fallback = extract_fallback_tool_calls(text)
            if fallback:
                calls = fallback
                text = strip_fallback_blocks(text)

        return text, calls

    def dispatch(self, name: str, args: dict) -> str:
        if name == "bash":
            return self.runner.bash(args.get("command", ""))
        if name == "read_file":
            return self.runner.read_file(args.get("path", ""), args.get("start"), args.get("end"))
        if name == "write_file":
            return self.runner.write_file(args.get("path", ""), args.get("content", ""), args.get("mode", "overwrite"))
        if name == "edit_file":
            return self.runner.edit_file(args.get("path", ""), args.get("old", ""), args.get("new", ""), args.get("count", 1))
        if name == "list_dir":
            return self.runner.list_dir(args.get("path", "."))
        if name == "run_python":
            return self.runner.run_python(args.get("code", ""))
        if name == "git":
            return self.runner.git(args.get("args", ""))
        if name == "http_get":
            return self.runner.http_get(args.get("url", ""))
        if name.startswith("skill_"):
            return run_skill(name[6:], args)
        known = ", ".join(sorted(NATIVE_TOOL_NAMES)) + (", " + ", ".join(f"skill_{s}" for s in SKILLS_REGISTRY) if SKILLS_REGISTRY else "")
        return f"Erreur : l'outil '{name}' n'existe pas. Outils disponibles : {known}."

    def turn(self, model: str, messages: list) -> list:
        """Exécute un tour complet (jusqu'à boucle max, réponse finale, ou répétition détectée)."""
        loops = 0
        max_loops = self.cfg.get("max_loops", 24)
        last_signature = None
        repeat_count = 0
        empty_retry_used = False
        while loops < max_loops:
            loops += 1
            messages = trim_history(messages, self.cfg.get("max_history_messages", 60))
            text, calls = self.call_model(model, messages)

            if not calls:
                if not text.strip():
                    if not empty_retry_used:
                        empty_retry_used = True
                        messages.append({
                            "role": "user",
                            "content": "(Réponds maintenant en texte clair avec ta réponse finale, sans appeler d'outil.)",
                        })
                        continue
                    empty_notice = (
                        "[odev] Le modèle n'a renvoyé aucune réponse exploitable "
                        "(ni outil, ni texte) après avoir consulté les informations "
                        "nécessaires. C'est une limite courante des très petits modèles "
                        "(<3B) sur les tâches en plusieurs étapes — réessaie la demande "
                        "directement, ou utilise un modèle plus capable "
                        "(ex: qwen2.5-coder:7b) pour ce type de synthèse."
                    )
                    self.on_text(empty_notice)
                    messages.append({"role": "assistant", "content": empty_notice})
                else:
                    self.on_text(text)
                    messages.append({"role": "assistant", "content": text})
                return messages

            if text.strip():
                self.on_text(text)

            # Détecte un appel identique répété (signe d'un modèle bloqué/trop petit)
            signature = json.dumps(sorted(calls), sort_keys=True, default=str)
            if signature == last_signature:
                repeat_count += 1
            else:
                repeat_count = 0
            last_signature = signature

            tool_calls_payload = [
                {"function": {"name": name, "arguments": args}} for name, args in calls
            ]
            messages.append({
                "role": "assistant",
                "content": text or "",
                "tool_calls": tool_calls_payload,
            })

            if repeat_count >= 2:
                warning = (
                    "[odev] Le même appel d'outil a été répété 3 fois de suite sans "
                    "progresser. Arrêt de ce tour pour éviter une boucle infinie — "
                    "reformule ta demande ou utilise un modèle plus capable pour le "
                    "tool-calling (ex: qwen2.5-coder:7b ou plus)."
                )
                messages.append({"role": "tool", "content": warning, "name": "_loop_guard"})
                self.on_tool_result("_loop_guard", warning)
                messages.append({"role": "assistant", "content": warning})
                return messages

            for name, args in calls:
                self.on_tool_start(name, args)
                result = self.dispatch(name, args)
                self.on_tool_result(name, result)
                messages.append({"role": "tool", "content": result, "name": name})

        messages.append({
            "role": "assistant",
            "content": f"[Arrêt : limite de {max_loops} itérations d'outils atteinte pour ce tour. Demande-moi de continuer si besoin.]",
        })
        return messages