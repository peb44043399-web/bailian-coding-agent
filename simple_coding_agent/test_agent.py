from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from simple_coding_agent.agent import AgentError, CodingAgent
from simple_coding_agent.course_map import LESSONS, render_course_map


def tool_call(call_id: str, name: str, arguments: dict):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=name,
            arguments=json.dumps(arguments),
        ),
    )


def response(content: str = "", calls=None):
    message = SimpleNamespace(content=content, tool_calls=calls or [])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class ScriptedCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if not self.responses:
            raise AssertionError("no scripted model response left")
        return self.responses.pop(0)


def fake_client(responses):
    completions = ScriptedCompletions(responses)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    return client, completions


class CodingAgentTests(unittest.TestCase):
    def make_agent(self, workspace: Path, responses=()):
        client, completions = fake_client(responses)
        agent = CodingAgent(
            client=client,
            model="fake-model",
            workspace=workspace,
            approve_shell=True,
            max_turns=8,
            enable_memory=False,
        )
        return agent, completions

    def test_file_tools_and_workspace_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent, _ = self.make_agent(root)

            self.assertIn("Wrote", agent._write_file("pkg/a.py", "x = 1\n"))
            self.assertIn("1  x = 1", agent._read_file("pkg/a.py"))
            self.assertEqual(agent._edit_file("pkg/a.py", "1", "2"), "Edited pkg/a.py")
            self.assertEqual((root / "pkg/a.py").read_text(), "x = 2\n")
            self.assertIn("pkg/a.py", agent._glob("**/*.py"))

            with self.assertRaises(AgentError):
                agent._safe_path("../outside.txt")
            dispatched = agent._dispatch(
                "read_file", json.dumps({"path": "../outside.txt"})
            )
            self.assertIn("path is outside the workspace", dispatched)

    def test_edit_requires_unique_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("same same")
            agent, _ = self.make_agent(root)
            self.assertEqual(
                agent._edit_file("a.txt", "same", "new"),
                "Error: expected exactly 1 match, found 2",
            )

    def test_write_refuses_existing_file_without_explicit_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "README.md"
            target.write_text("original\n")
            agent, _ = self.make_agent(root)

            result = agent._write_file("README.md", "replacement\n")

            self.assertIn("file already exists", result)
            self.assertIn("overwrite=true", result)
            self.assertEqual(target.read_text(), "original\n")
            self.assertEqual(agent._change_revision, 0)

    def test_explicit_overwrite_requires_and_records_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "README.md"
            target.write_text("original\n")
            client, _ = fake_client([])
            requested_actions = []
            denied_agent = CodingAgent(
                client=client,
                model="fake-model",
                workspace=root,
                approve_shell=False,
                approval_callback=lambda action: requested_actions.append(action) or False,
                enable_memory=False,
            )

            denied = denied_agent._write_file(
                "README.md", "replacement\n", overwrite=True
            )

            self.assertEqual(denied, "Permission denied by user")
            self.assertEqual(target.read_text(), "original\n")
            self.assertEqual(
                requested_actions, ["overwrite existing file: README.md"]
            )

            approved_agent, _ = self.make_agent(root)
            approved = approved_agent._write_file(
                "README.md", "replacement\n", overwrite=True
            )
            self.assertIn("Wrote", approved)
            self.assertEqual(target.read_text(), "replacement\n")
            self.assertEqual(approved_agent._change_revision, 1)

    def test_write_tool_schema_exposes_boolean_overwrite_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            agent, _ = self.make_agent(Path(directory))
            write_tool = next(
                tool
                for tool in agent._tool_definitions()
                if tool["function"]["name"] == "write_file"
            )
            overwrite = write_tool["function"]["parameters"]["properties"][
                "overwrite"
            ]
            self.assertEqual(overwrite["type"], "boolean")
            self.assertFalse(overwrite["default"])

    def test_agent_loop_cannot_silently_overwrite_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "README.md"
            target.write_text("project documentation\n")
            client, completions = fake_client(
                [
                    response(
                        calls=[
                            tool_call(
                                "write-existing",
                                "write_file",
                                {
                                    "path": "README.md",
                                    "content": "unrequested replacement\n",
                                },
                            )
                        ]
                    ),
                    response("The host refused the unsafe replacement."),
                ]
            )
            agent = CodingAgent(
                client=client,
                model="fake-model",
                workspace=root,
                approve_shell=True,
                max_turns=4,
                enable_memory=False,
            )

            result = agent.run("Create a separate example without changing README.md")

            self.assertEqual(target.read_text(), "project documentation\n")
            self.assertEqual(result.changed_files, ())
            tool_result = completions.requests[1]["messages"][-1]["content"]
            self.assertIn("file already exists", tool_result)

    def test_dangerous_shell_is_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            agent, _ = self.make_agent(Path(directory))
            result = agent._run_command("git reset --hard", verify=False)
            self.assertIn("Permission denied", result)

    def test_todo_skill_and_readonly_subagent_tool_pool(self):
        with tempfile.TemporaryDirectory() as directory:
            agent, _ = self.make_agent(Path(directory))
            rendered = agent._todo_write(
                [
                    {"content": "inspect", "status": "completed"},
                    {"content": "implement", "status": "in_progress"},
                ]
            )
            self.assertIn("[in_progress] implement", rendered)
            self.assertIn("agent-builder", agent._skills)
            self.assertIn("Source:", agent._load_skill("agent-builder"))

            agent.allowed_tools = {"read_file", "glob", "search_text", "load_skill"}
            names = {
                tool["function"]["name"] for tool in agent._tool_definitions()
            }
            self.assertEqual(
                names, {"read_file", "glob", "search_text", "load_skill"}
            )

    def test_context_compaction_preserves_recent_tool_results(self):
        with tempfile.TemporaryDirectory() as directory:
            agent, _ = self.make_agent(Path(directory))
            agent.messages = [
                {
                    "role": "tool",
                    "tool_call_id": f"call-{index}",
                    "content": str(index) * 1000,
                }
                for index in range(5)
            ]

            compacted = agent._messages_for_model()

            self.assertIn("Earlier tool result omitted", compacted[0]["content"])
            self.assertEqual(compacted[2]["content"], "2" * 1000)
            self.assertEqual(agent.messages[0]["content"], "0" * 1000)

    def test_course_map_covers_exactly_s01_to_s17(self):
        self.assertEqual(
            [lesson.stage for lesson in LESSONS],
            [f"s{index:02d}" for index in range(1, 18)],
        )
        rendered = render_course_map()
        self.assertIn("s15  Integrated Harness", rendered)
        self.assertIn("s17  Goal Loop", rendered)

    def test_stop_hook_requires_successful_verification_after_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            client, completions = fake_client(
                [
                    response(
                        calls=[
                            tool_call(
                                "write-1",
                                "write_file",
                                {"path": "answer.py", "content": "VALUE = 42\n"},
                            )
                        ]
                    ),
                    response("Finished too early"),
                    response(
                        calls=[
                            tool_call(
                                "verify-1",
                                "verify",
                                {"command": "python -m py_compile answer.py"},
                            )
                        ]
                    ),
                    response("Implemented and verified."),
                ]
            )
            agent = CodingAgent(
                client=client,
                model="fake-model",
                workspace=root,
                approve_shell=True,
                max_turns=8,
                enable_memory=False,
            )

            result = agent.run("Create answer.py")

            self.assertEqual(result.text, "Implemented and verified.")
            self.assertEqual(result.changed_files, ("answer.py",))
            self.assertIn("exit_code=0", result.verification or "")
            stop_request = completions.requests[2]["messages"][-1]["content"]
            self.assertIn("Stop hook blocked completion", stop_request)


if __name__ == "__main__":
    unittest.main()
