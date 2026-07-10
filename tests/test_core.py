import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path
import unittest


def import_with_temp_home(module_name: str, temp_home: Path):
    os.environ["ODEV_HOME"] = str(temp_home)
    for name in list(sys.modules):
        if name == "odev" or name.startswith("odev."):
            sys.modules.pop(name)
    return importlib.import_module(module_name)


class MemoryTests(unittest.TestCase):
    def test_memory_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_home = Path(tmp)
            memory_module = import_with_temp_home("odev.memory", temp_home)
            memory = memory_module.load_memory()
            memory_module.set_project_summary(memory, "CLI agent local")
            memory_module.add_task(memory, "Écrire les tests")
            memory_module.add_note(memory, "Préférer apply_patch")

            reloaded = memory_module.load_memory()
            self.assertEqual(reloaded["project_summary"], "CLI agent local")
            self.assertEqual(reloaded["active_tasks"][0]["title"], "Écrire les tests")
            self.assertIn("Préférer apply_patch", reloaded["notes"])

    def test_render_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_home = Path(tmp)
            memory_module = import_with_temp_home("odev.memory", temp_home)
            memory = {
                "project_summary": "Résumé",
                "active_tasks": [{"id": 1, "title": "Tester", "done": False}],
                "notes": ["Note"],
            }
            rendered = memory_module.render_memory(memory)
            self.assertIn("Résumé projet:", rendered)
            self.assertIn("#1 Tester", rendered)
            self.assertIn("Notes récentes:", rendered)


class ToolTests(unittest.TestCase):
    def test_run_python_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_home = Path(tmp)
            tools_module = import_with_temp_home("odev.tools", temp_home)
            runner = tools_module.ToolRunner({})
            output = runner.run_python("import sys\nprint(sys.flags.isolated)")
            self.assertIn("1", output)

    @unittest.skipUnless(shutil.which("patch"), "patch command not available")
    def test_apply_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_home = Path(tmp)
            tools_module = import_with_temp_home("odev.tools", temp_home)
            runner = tools_module.ToolRunner({})
            runner.cwd = str(temp_home)
            target = temp_home / "sample.txt"
            target.write_text("hello\nworld\n", encoding="utf-8")
            patch_text = """--- a/sample.txt
+++ b/sample.txt
@@ -1,2 +1,2 @@
-hello
+hola
"""
            result = runner.apply_patch(patch_text)
            self.assertNotIn("Erreur patch", result)
            self.assertIn("hola", target.read_text(encoding="utf-8"))


class AgentHelpersTests(unittest.TestCase):
    def test_extract_fallback_tool_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_home = Path(tmp)
            agent_module = import_with_temp_home("odev.agent", temp_home)
            calls = agent_module.extract_fallback_tool_calls(
                "```bash\npwd\n```\n```json\n{\"name\": \"read_file\", \"arguments\": {\"path\": \"README.md\"}}\n```"
            )
            self.assertEqual(calls[0][0], "bash")
            self.assertEqual(calls[1][0], "read_file")

    def test_trim_history_keeps_system_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_home = Path(tmp)
            agent_module = import_with_temp_home("odev.agent", temp_home)
            messages = [{"role": "system", "content": "system"}]
            for index in range(10):
                messages.append({"role": "user", "content": f"u{index}"})
                messages.append({"role": "assistant", "content": f"a{index}"})
            trimmed = agent_module.trim_history(messages, 4)
            self.assertEqual(trimmed[0]["role"], "system")
            self.assertLessEqual(len(trimmed), 5)


class SkillLoadingTests(unittest.TestCase):
    def test_local_skills_are_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_home = Path(tmp)
            skills_module = import_with_temp_home("odev.skills", temp_home)
            loaded, errors = skills_module.load_skills()
            self.assertFalse(errors)
            for expected in {
                "code_review",
                "code_review_deep",
                "tdd_guide",
                "bug_triage",
                "refactor_planner",
                "api_review",
                "debug_python",
                "test_generator",
                "architecture_mapper",
                "ci_triage",
                "generate_docs",
            }:
                self.assertIn(expected, loaded)
                self.assertIn(expected, skills_module.SKILLS_REGISTRY)
            schema_names = [item["function"]["name"] for item in skills_module.skill_tool_schemas()]
            self.assertIn("skill_code_review", schema_names)


class UiStyleTests(unittest.TestCase):
    def test_style_switching(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_home = Path(tmp)
            try:
                ui_module = import_with_temp_home("odev.ui", temp_home)
            except ModuleNotFoundError as exc:
                if exc.name == "rich":
                    self.skipTest("rich is not installed in this environment")
                raise
            self.assertIn("codex", ui_module.available_styles())
            self.assertEqual(ui_module.set_style("claude"), "claude")
            self.assertEqual(ui_module.get_style(), "claude")
            self.assertEqual(ui_module.set_style("gemini"), "gemini")


if __name__ == "__main__":
    unittest.main()
