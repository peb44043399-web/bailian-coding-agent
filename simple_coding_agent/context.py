"""OpenAI-message adaptation of the complete s08 context compaction pipeline."""

from __future__ import annotations

import copy
import json
import re
import uuid
from pathlib import Path
from typing import Callable


class ContextCompactor:
    """Archive, reduce, summarize, and reactively recover oversized context.

    REUSE[s08_context_compact/code.py::ContextCompactor]: the four stages are
    preserved, while Anthropic tool blocks are adapted to OpenAI's assistant
    ``tool_calls`` plus individual ``role=tool`` messages.
    """

    CONTEXT_CHAR_LIMIT = 50_000
    TOOL_RESULT_BATCH_CHAR_LIMIT = 200_000
    LARGE_RESULT_CHAR_LIMIT = 30_000
    SUMMARY_INPUT_CHAR_LIMIT = 80_000
    KEEP_RECENT_RESULTS = 3
    KEEP_RECENT_MESSAGES = 5
    MAX_MESSAGES = 50

    def __init__(
        self,
        *,
        workspace: Path,
        summarize: Callable[[str], str],
        emit: Callable[[str], None] | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.transcript_dir = self.workspace / ".transcripts"
        self.tool_results_dir = self.workspace / ".task_outputs" / "tool-results"
        self.summarize = summarize
        self.emit = emit or (lambda _message: None)

    @staticmethod
    def estimate_chars(messages: list[dict]) -> int:
        return len(json.dumps(messages, default=str, ensure_ascii=False))

    @staticmethod
    def has_tool_calls(message: dict) -> bool:
        return message.get("role") == "assistant" and bool(message.get("tool_calls"))

    @staticmethod
    def is_tool_result(message: dict) -> bool:
        return message.get("role") == "tool"

    def write_transcript(self, messages: list[dict]) -> Path:
        self.transcript_dir.mkdir(parents=True, exist_ok=True)
        path = self.transcript_dir / f"transcript_{uuid.uuid4().hex}.jsonl"
        with path.open("x", encoding="utf-8") as transcript:
            for message in messages:
                transcript.write(
                    json.dumps(message, default=str, ensure_ascii=False) + "\n"
                )
        return path

    def persist_large_output(self, tool_call_id: str, output: str) -> str:
        if len(output) <= self.LARGE_RESULT_CHAR_LIMIT:
            return output
        self.tool_results_dir.mkdir(parents=True, exist_ok=True)
        safe_id = re.sub(r"[^A-Za-z0-9._-]", "_", str(tool_call_id))[:120]
        path = self.tool_results_dir / f"{safe_id or 'unknown'}.txt"
        if not path.exists():
            path.write_text(output, encoding="utf-8")
        self.emit(
            f"[context] tool_result_budget persisted {len(output)} chars -> {path}"
        )
        return (
            f"<persisted-output>\nFull output: {path}\nPreview:\n"
            f"{output[:2000]}\n</persisted-output>"
        )

    def tool_result_budget(
        self, messages: list[dict], max_chars: int | None = None
    ) -> list[dict]:
        if not messages or not self.is_tool_result(messages[-1]):
            return messages
        batch: list[dict] = []
        for message in reversed(messages):
            if not self.is_tool_result(message):
                break
            batch.append(message)
        limit = max_chars or self.TOOL_RESULT_BATCH_CHAR_LIMIT
        total = sum(len(str(message.get("content", ""))) for message in batch)
        for message in sorted(
            batch,
            key=lambda item: len(str(item.get("content", ""))),
            reverse=True,
        ):
            if total <= limit:
                break
            output = str(message.get("content", ""))
            if len(output) <= self.LARGE_RESULT_CHAR_LIMIT:
                continue
            message["content"] = self.persist_large_output(
                str(message.get("tool_call_id", "unknown")), output
            )
            total = sum(len(str(item.get("content", ""))) for item in batch)
        return messages

    def snip_compact(
        self, messages: list[dict], max_messages: int | None = None
    ) -> list[dict]:
        maximum = max_messages or self.MAX_MESSAGES
        if len(messages) <= maximum:
            return messages
        head_end = min(3, len(messages))
        tail_start = len(messages) - (maximum - head_end)

        # Never retain an assistant tool call without its following results.
        if head_end and self.has_tool_calls(messages[head_end - 1]):
            while head_end < tail_start and self.is_tool_result(messages[head_end]):
                head_end += 1

        # Never start the retained tail in the middle of a tool-call batch.
        if tail_start < len(messages) and self.is_tool_result(messages[tail_start]):
            while tail_start > 0 and self.is_tool_result(messages[tail_start]):
                tail_start -= 1
            if tail_start > 0 and not self.has_tool_calls(messages[tail_start]):
                tail_start += 1

        if head_end >= tail_start:
            return messages
        transcript = self.write_transcript(messages)
        archived = tail_start - head_end
        marker = {
            "role": "user",
            "content": f"[{archived} messages archived at {transcript}]",
        }
        self.emit(
            f"[context] snip_compact archived {archived} messages -> {transcript}"
        )
        return [*messages[:head_end], marker, *messages[tail_start:]]

    def micro_compact(self, messages: list[dict]) -> list[dict]:
        results = [message for message in messages if self.is_tool_result(message)]
        compacted = 0
        for message in results[: -self.KEEP_RECENT_RESULTS]:
            content = str(message.get("content", ""))
            if len(content) <= 120:
                continue
            saved_path = next(
                (
                    line.removeprefix("Full output: ")
                    for line in content.splitlines()
                    if line.startswith("Full output: ")
                ),
                None,
            )
            message["content"] = (
                f"[Earlier tool result saved at {saved_path}]"
                if saved_path
                else "[Earlier tool result omitted.]"
            )
            compacted += 1
        if compacted:
            self.emit(f"[context] micro_compact reduced {compacted} old tool results")
        return messages

    def summary_input(self, messages: list[dict]) -> str:
        conversation = json.dumps(messages, default=str, ensure_ascii=False)
        if len(conversation) <= self.SUMMARY_INPUT_CHAR_LIMIT:
            return conversation
        head = self.SUMMARY_INPUT_CHAR_LIMIT // 4
        tail = self.SUMMARY_INPUT_CHAR_LIMIT - head
        return (
            conversation[:head]
            + "\n...[middle omitted; full transcript is on disk]...\n"
            + conversation[-tail:]
        )

    @staticmethod
    def summary_message(
        label: str, request: str, summary: str, transcript: Path
    ) -> dict:
        return {
            "role": "user",
            "content": (
                f"[{label}]\n\nCurrent user request:\n{request}\n\n"
                "Conversation summary (reference only):\n"
                f"{json.dumps(summary, ensure_ascii=False)}\n\n"
                f"Full transcript: {transcript}"
            ),
        }

    def compact_history(
        self, messages: list[dict], active_request: str, *, label: str = "Compacted"
    ) -> list[dict]:
        transcript = self.write_transcript(messages)
        self.emit(f"[context] {label.lower()} transcript saved -> {transcript}")
        summary = self.summarize(self.summary_input(messages)).strip() or "(empty summary)"
        self.emit(
            f"[context] {label.lower()} {len(messages)} messages into "
            f"{len(summary)} summary chars"
        )
        return [self.summary_message(label, active_request, summary, transcript)]

    def reactive_compact(
        self, messages: list[dict], active_request: str
    ) -> list[dict]:
        transcript = self.write_transcript(messages)
        tail_start = max(0, len(messages) - self.KEEP_RECENT_MESSAGES)
        if tail_start and self.is_tool_result(messages[tail_start]):
            while tail_start > 0 and self.is_tool_result(messages[tail_start]):
                tail_start -= 1
        old_history = messages[:tail_start] if tail_start else messages
        summary = self.summarize(self.summary_input(old_history)).strip() or "(empty summary)"
        message = self.summary_message(
            "Reactive compact", active_request, summary, transcript
        )
        self.emit(
            f"[context] reactive_compact retained {len(messages) - tail_start} "
            f"recent messages; transcript -> {transcript}"
        )
        return [message, *messages[tail_start:]] if tail_start else [message]

    def prepare(self, messages: list[dict], active_request: str) -> list[dict]:
        prepared = copy.deepcopy(messages)
        prepared = self.tool_result_budget(prepared)
        prepared = self.snip_compact(prepared)
        prepared = self.micro_compact(prepared)
        size = self.estimate_chars(prepared)
        self.emit(f"[context] prepared {len(prepared)} messages · {size} chars")
        if size > self.CONTEXT_CHAR_LIMIT:
            self.emit(
                f"[context] auto compact triggered at {size} chars "
                f"(limit {self.CONTEXT_CHAR_LIMIT})"
            )
            prepared = self.compact_history(prepared, active_request)
        return prepared
