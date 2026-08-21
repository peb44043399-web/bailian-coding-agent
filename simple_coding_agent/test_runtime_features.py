from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from simple_coding_agent.agent import CodingAgent
from simple_coding_agent.context import ContextCompactor
from simple_coding_agent.memory import MemoryManager
from simple_coding_agent.test_agent import fake_client, response, tool_call


class ContextCompactorTests(unittest.TestCase):
    def test_four_stage_pipeline_persists_snips_micros_and_summarizes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events: list[str] = []
            compactor = ContextCompactor(
                workspace=root,
                summarize=lambda _conversation: "factual summary",
                emit=events.append,
            )
            compactor.LARGE_RESULT_CHAR_LIMIT = 20
            compactor.TOOL_RESULT_BATCH_CHAR_LIMIT = 25
            messages = [
                {"role": "user", "content": f"request {index} " + "x" * 40}
                for index in range(55)
            ]
            messages.extend(
                [
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "large-call",
                                "type": "function",
                                "function": {"name": "read_file", "arguments": "{}"},
                            }
                        ],
                    },
                    {
                        "role": "tool",
                        "tool_call_id": "large-call",
                        "content": "large-output-" * 20,
                    },
                ]
            )
            compactor.CONTEXT_CHAR_LIMIT = 200

            prepared = compactor.prepare(messages, "inspect project")

            self.assertEqual(len(prepared), 1)
            self.assertIn("factual summary", prepared[0]["content"])
            self.assertTrue(list((root / ".transcripts").glob("*.jsonl")))
            self.assertTrue(
                (root / ".task_outputs" / "tool-results" / "large-call.txt").is_file()
            )
            joined = "\n".join(events)
            self.assertIn("tool_result_budget persisted", joined)
            self.assertIn("snip_compact archived", joined)
            self.assertIn("auto compact triggered", joined)

    def test_micro_compact_preserves_recent_tool_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            compactor = ContextCompactor(
                workspace=Path(directory),
                summarize=lambda _conversation: "summary",
            )
            messages = [
                {"role": "tool", "tool_call_id": str(index), "content": "x" * 500}
                for index in range(5)
            ]

            compacted = compactor.micro_compact(messages)

            self.assertIn("omitted", compacted[0]["content"])
            self.assertEqual(compacted[2]["content"], "x" * 500)


class MemoryManagerTests(unittest.TestCase):
    def test_one_off_user_instruction_is_not_persistent_memory(self) -> None:
        candidate = {
            "name": "Explicit compact procedure",
            "type": "user",
            "scope": "persistent",
            "description": "Run Todo then compact for this check",
            "body": "First call todo_write, then compact, finally return done.",
        }

        self.assertFalse(
            MemoryManager.should_store(
                candidate,
                [],
                dialogue="user: First create a Todo, then compact, and answer done.",
            )
        )

    def test_select_extract_and_persist_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events: list[str] = []

            def complete(prompt: str, _max_tokens: int, _system: str) -> str:
                if "Select memory records" in prompt:
                    return "[0]"
                return json.dumps(
                    [
                        {
                            "name": "Testing preference",
                            "type": "user",
                            "scope": "persistent",
                            "description": "User requires real tests",
                            "body": "Always run relevant tests after implementation.",
                        },
                        {
                            "name": "Temporary task",
                            "type": "project",
                            "scope": "current_task",
                            "description": "Only for this task",
                            "body": "Temporary state.",
                        },
                    ],
                    ensure_ascii=False,
                )

            manager = MemoryManager(
                workspace=root,
                complete=complete,
                emit=events.append,
            )
            manager.store.write(
                "Project language",
                "project",
                "Project primarily uses Python",
                "Use the configured Conda Python environment.",
            )

            recalled = manager.recall(
                [{"role": "user", "content": "How should this Python project run?"}]
            )
            stored = manager.extract(
                [
                    {"role": "user", "content": "Please remember that real tests are required."},
                    {"role": "assistant", "content": "Understood."},
                ]
            )

            self.assertIn("project-language.md", recalled)
            self.assertEqual(stored, 1)
            self.assertTrue((root / ".memory" / "testing-preference.md").is_file())
            self.assertFalse((root / ".memory" / "temporary-task.md").exists())
            self.assertIn("Testing preference", manager.store.read_index())
            self.assertTrue(any("recalled 1" in event for event in events))


class VisibleRuntimeFeatureTests(unittest.TestCase):
    def test_todo_events_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            events: list[str] = []
            client, _ = fake_client([])
            agent = CodingAgent(
                client=client,
                model="fake-model",
                workspace=Path(directory),
                approve_shell=True,
                log_callback=events.append,
                enable_memory=False,
            )

            agent._todo_write(
                [
                    {"content": "inspect", "status": "completed"},
                    {"content": "implement", "status": "in_progress"},
                ]
            )

            self.assertTrue(any(event.startswith("[todo] plan updated") for event in events))
            self.assertTrue(any("[in_progress] implement" in event for event in events))

    def test_subagent_is_created_uses_research_tools_and_returns_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "module.py").write_text("NEEDLE = 42\n", encoding="utf-8")
            client, completions = fake_client(
                [
                    response(
                        calls=[
                            tool_call(
                                "task-1",
                                "task",
                                {"prompt": "Find NEEDLE and report its file and line."},
                            )
                        ]
                    ),
                    response(
                        calls=[
                            tool_call(
                                "search-1",
                                "search_text",
                                {"query": "NEEDLE", "pattern": "**/*.py"},
                            )
                        ]
                    ),
                    response("Found NEEDLE at module.py:1."),
                    response("Subagent evidence confirms module.py:1."),
                ]
            )
            events: list[str] = []
            agent = CodingAgent(
                client=client,
                model="fake-model",
                workspace=root,
                approve_shell=True,
                max_turns=6,
                log_callback=events.append,
                enable_memory=False,
            )

            result = agent.run("Delegate repository research before answering.")

            self.assertEqual(len(result.subagents), 1)
            subagent_id = result.subagents[0]
            self.assertTrue(any(f"created id={subagent_id}" in event for event in events))
            self.assertTrue(any(f"completed id={subagent_id}" in event for event in events))
            child_tools = {
                item["function"]["name"] for item in completions.requests[1]["tools"]
            }
            self.assertEqual(
                child_tools, {"read_file", "glob", "search_text", "load_skill"}
            )
            self.assertIn("module.py:1", completions.requests[2]["messages"][-1]["content"])
            self.assertIn(
                f"Subagent {subagent_id} completed",
                completions.requests[3]["messages"][-1]["content"],
            )

    def test_explicit_compact_tool_archives_and_summarizes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client, completions = fake_client(
                [
                    response(calls=[tool_call("compact-1", "compact", {})]),
                    response("Conversation summarized with current goal preserved."),
                    response("Continued after explicit compaction."),
                ]
            )
            events: list[str] = []
            agent = CodingAgent(
                client=client,
                model="fake-model",
                workspace=Path(directory),
                approve_shell=True,
                max_turns=4,
                log_callback=events.append,
                enable_memory=False,
            )

            result = agent.run("Demonstrate explicit context compaction.")

            self.assertEqual(result.text, "Continued after explicit compaction.")
            self.assertTrue(any("explicit compact" in event for event in events))
            self.assertIn(
                "Conversation summarized",
                completions.requests[2]["messages"][-1]["content"],
            )
            self.assertIn(
                "explicit context compaction has completed",
                completions.requests[2]["messages"][-1]["content"],
            )
            self.assertNotIn(
                "compact",
                {
                    tool["function"]["name"]
                    for tool in completions.requests[2]["tools"]
                },
            )


if __name__ == "__main__":
    unittest.main()
