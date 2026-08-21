"""Presentation-neutral parsers for coding-agent GUI runtime events."""

from __future__ import annotations

import re
from typing import Any


SIDEBAR_ONLY_ACTIVITY = frozenset({"todo", "subagent"})


def compact_path(value: str, max_characters: int = 42) -> str:
    """Keep the useful path tail when horizontal space is limited."""

    if len(value) <= max_characters:
        return value
    return "…" + value[-(max_characters - 1) :]


def classify_activity(line: str) -> str:
    """Map a host log line to one visual activity category."""

    stripped = line.strip()
    if stripped.startswith("[tool]"):
        return "tool"
    if stripped.startswith(">"):
        return "tool_result"
    if stripped.startswith("[subagent]"):
        return "subagent"
    if stripped.startswith("[todo]"):
        return "todo"
    if stripped.startswith("[memory]"):
        return "memory"
    if stripped.startswith("[stop]"):
        return "success"
    if stripped.startswith("[context]"):
        return "warning"
    if stripped.startswith("[workspace]"):
        return "meta"
    if stripped.startswith("[error]"):
        return "error"
    return "meta"


def parse_todo_event(line: str) -> dict[str, Any] | None:
    """Parse one visible ``[todo]`` event for the inspector projection."""

    stripped = line.strip()
    if not stripped.startswith("[todo]"):
        return None
    body = stripped[len("[todo]") :].strip()
    if body == "plan cleared":
        return {"kind": "clear"}
    summary = re.fullmatch(
        r"plan updated · (\d+) step\(s\) · (\d+) completed", body
    )
    if summary:
        return {
            "kind": "summary",
            "total": int(summary.group(1)),
            "completed": int(summary.group(2)),
        }
    item = re.fullmatch(
        r"(\d+)\. \[(pending|in_progress|completed)\] (.+)", body
    )
    if item:
        return {
            "kind": "item",
            "index": int(item.group(1)),
            "status": item.group(2),
            "content": item.group(3).strip(),
        }
    return None


def parse_subagent_event(line: str) -> dict[str, Any] | None:
    """Parse lifecycle/tool events emitted by the bounded s06 subagent."""

    stripped = line.strip()
    if not stripped.startswith("[subagent]"):
        return None
    body = stripped[len("[subagent]") :].strip()
    created = re.fullmatch(
        r"created id=([\w-]+) mode=([\w-]+) tools=(.*)", body
    )
    if created:
        tools = [name for name in created.group(3).split(",") if name]
        return {
            "kind": "created",
            "id": created.group(1),
            "mode": created.group(2),
            "tool_count": len(tools),
        }
    completed = re.fullmatch(
        r"completed id=([\w-]+) turns=(\d+) tool_calls=(\d+)", body
    )
    if completed:
        return {
            "kind": "completed",
            "id": completed.group(1),
            "turns": int(completed.group(2)),
            "tool_calls": int(completed.group(3)),
        }
    failed = re.fullmatch(r"failed id=([\w-]+):\s*(.*)", body)
    if failed:
        return {
            "kind": "failed",
            "id": failed.group(1),
            "error": failed.group(2).strip(),
        }
    tool = re.match(r"id=([\w-]+) \[tool\] ([\w-]+)", body)
    if tool:
        return {"kind": "tool", "id": tool.group(1), "tool": tool.group(2)}
    return None
