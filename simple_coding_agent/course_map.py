"""The complete s01-s17 learning map shown by the GUI.

This is deliberately a map, not seventeen copied runtimes.  The course itself
states that s15 is cumulative while s16 and s17 are focused mechanism examples.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Lesson:
    stage: str
    topic: str
    source: str
    use_here: str


LESSONS = (
    Lesson("s01", "Agent Loop", "s01_agent_loop/code.py", "主循环：模型→工具→结果→继续/停止"),
    Lesson("s02", "Tool Use", "s02_tool_use/code.py", "工具 schema 与名称分发；已落地"),
    Lesson("s03", "Permission", "s03_permission/code.py", "工作区路径边界、硬拒绝、命令审批；已落地"),
    Lesson("s04", "Hooks", "s04_hooks/code.py", "User/Pre/Post/Stop 扩展点；已落地"),
    Lesson("s05", "TodoWrite", "s05_todo_write/code.py", "多步骤任务的短计划；已落地"),
    Lesson("s06", "Subagent", "s06_subagent/code.py", "带运行 ID、独立 messages[] 和跨文件搜索的只读研究子任务；已落地"),
    Lesson("s07", "Skill Loading", "s07_skill_loading/code.py", "只预载目录、按需加载 SKILL.md；已落地"),
    Lesson("s08", "Context Compact", "s08_context_compact/code.py", "结果落盘、消息裁剪、微压缩、摘要和反应式重试；已完整适配"),
    Lesson("s09", "Memory", "s09_memory/code.py", "选择、召回、提取、整理并持久化到 .memory；已落地"),
    Lesson("s10", "Task System", "s10_task_system/code.py", "单人默认链使用显式 Todo；持久任务图仍直接学习原章"),
    Lesson("s11", "Background Tasks", "s11_background_tasks/code.py", "GUI 将 Agent 放工作线程；通用后台命令管理见原章"),
    Lesson("s12", "Cron Scheduler", "s12_cron_scheduler/code.py", "不属于即时 coding 必需路径；调度实现复用原章"),
    Lesson("s13", "Agent Teams", "s13_agent_teams/code.py", "默认单 Agent；持久队友、协议、worktree 复用原章"),
    Lesson("s14", "MCP Plugin", "s14_mcp_plugin/code.py", "默认本地工具已足够；Mock MCP 教学实现复用原章"),
    Lesson("s15", "Integrated Harness", "s15_integrated_harness/code.py", "多机制仍共用一个 loop 的总体结构；已落地"),
    Lesson("s16", "Workflow Runtime", "s16_workflow_runtime/code.py", "宿主固定工具/编排边界；本应用固定 verify gate"),
    Lesson("s17", "Goal Loop", "s17_goal_loop/code.py", "停止候选经宿主检查；修改后未验证则拒绝结束"),
)


def render_course_map() -> str:
    lines = [
        "s01–s17 完整知识地图",
        "",
        "默认运行路径只启用完成单人 coding 任务直接需要的机制。",
        "其余章节保留到原始 code.py，避免复制后产生两套难以对照的代码。",
        "",
    ]
    for lesson in LESSONS:
        lines.extend(
            [
                f"{lesson.stage}  {lesson.topic}",
                f"  来源：{lesson.source}",
                f"  本应用：{lesson.use_here}",
                "",
            ]
        )
    lines.extend(
        [
            "边界说明",
            "  s15 是 s01–s15 的累计集成示例。",
            "  s16、s17 是聚焦机制示例，不是继续叠加后的大一统运行时。",
            "  Worktree 只隔离 checkout/branch，不是安全沙箱。",
            "  课程 s14 的 MCP 是进程内教学替身，不代表真实外部 MCP E2E。",
        ]
    )
    return "\n".join(lines)
