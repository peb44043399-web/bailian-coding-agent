from __future__ import annotations

import os
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from simple_coding_agent.gui_events import (  # noqa: E402
    SIDEBAR_ONLY_ACTIVITY,
    classify_activity,
    compact_path,
    parse_subagent_event,
    parse_todo_event,
)
from simple_coding_agent.qt_gui import CodingAgentWindow  # noqa: E402


class GuiEventParserTests(unittest.TestCase):
    def test_compact_path_keeps_tail_for_long_value(self) -> None:
        value = "/Users/example/Desktop/a-very-long-project-name/source"
        compacted = compact_path(value, max_characters=24)
        self.assertEqual(len(compacted), 24)
        self.assertTrue(compacted.startswith("…"))
        self.assertTrue(compacted.endswith("project-name/source"))

    def test_activity_categories_match_runtime_events(self) -> None:
        cases = {
            "[tool] read_file {}": "tool",
            "> verify: exit_code=0": "tool_result",
            "[subagent] started": "subagent",
            "[todo] 1. [in_progress] implement": "todo",
            "[memory] recalled 1 record": "memory",
            "[stop] verified": "success",
            "[context] compacted": "warning",
            "[workspace] /tmp/project": "meta",
            "[error] failed": "error",
        }
        for line, expected in cases.items():
            with self.subTest(line=line):
                self.assertEqual(classify_activity(line), expected)
        self.assertEqual(SIDEBAR_ONLY_ACTIVITY, {"todo", "subagent"})

    def test_todo_and_subagent_events_are_parsed(self) -> None:
        self.assertEqual(
            parse_todo_event("[todo] plan updated · 3 step(s) · 1 completed"),
            {"kind": "summary", "total": 3, "completed": 1},
        )
        self.assertEqual(
            parse_todo_event("[todo] 2. [in_progress] 修复根因"),
            {
                "kind": "item",
                "index": 2,
                "status": "in_progress",
                "content": "修复根因",
            },
        )
        self.assertEqual(
            parse_subagent_event(
                "[subagent] completed id=223084a2 turns=3 tool_calls=2"
            ),
            {
                "kind": "completed",
                "id": "223084a2",
                "turns": 3,
                "tool_calls": 2,
            },
        )


class QtGuiProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = CodingAgentWindow(
            initial_workspace=Path.cwd(),
            initial_model="qwen3-coder-plus",
            base_url="https://example.invalid",
            max_turns=20,
            command_timeout=120,
            enable_thinking=False,
        )

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()

    def test_todo_and_subagent_logs_project_to_inspector(self) -> None:
        self.window._append_log("[todo] plan updated · 2 step(s) · 0 completed")
        self.window._append_log("[todo] 1. [in_progress] inspect root cause")
        self.window._append_log(
            "[subagent] created id=abc123 mode=read-only tools=glob,read_file"
        )

        self.assertEqual(self.window.plan_panel.count.text(), "0 / 2")
        self.assertEqual(self.window.subagent_panel.count.text(), "1")
        self.assertEqual(self.window._activity_count, 0)

    def test_result_updates_changes_and_completion_state(self) -> None:
        result = SimpleNamespace(
            text="Implemented and verified.",
            changed_files=("src/app.py", "tests/test_app.py"),
            turns=4,
            tool_calls=6,
            verification="pytest: exit_code=0",
        )

        self.window._handle_result(result)

        self.assertEqual(self.window.changes_panel.count.text(), "2 files")
        self.assertEqual(self.window.status_pill.property("state"), "complete")
        self.assertEqual(self.window.run_state_title.text(), "Completed")
        self.assertGreaterEqual(self.window._activity_count, 3)


if __name__ == "__main__":
    unittest.main()
