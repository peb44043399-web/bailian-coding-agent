# s01–s17 复用与边界表

“复用”有两种：运行时代码结构适配，以及直接把原章作为学习入口。后者不复制代码，避免教材和成品产生两套实现。

| 章节 | 原始实现 | 本应用位置 | 复用方式 |
|---|---|---|---|
| s01 Agent Loop | `s01_agent_loop/code.py::agent_loop` | `agent.py::CodingAgent.run` | 保留一个循环；消息格式改为百炼 OpenAI 兼容格式 |
| s02 Tool Use | `TOOLS`、`TOOL_HANDLERS`、`safe_path` | `TOOLS`、`_dispatch`、`_safe_path` | 结构适配 |
| s03 Permission | deny/rule/approval 三闸门 | `_permission_hook`、`_run_command` | 结构适配；GUI 负责逐条审批 |
| s04 Hooks | `HOOKS`、`trigger_hooks` | `_hooks`、`_trigger_hooks` | 结构适配 |
| s05 TodoWrite | `run_todo_write` | `_todo_write` | 状态约束适配 |
| s06 Subagent | `run_subagent` | `_run_subagent` | fresh `messages[]`、可追踪 ID；限制为只读但增加跨文件文本搜索 |
| s07 Skill Loading | `SkillLoader` | `_scan_skills`、`_load_skill` | 目录先行、正文按需加载 |
| s08 Context Compact | `tool_result_budget`、`snip_compact`、`micro_compact`、`compact_history`、`reactive_compact` | `context.py::ContextCompactor`、`compact` 工具 | 四层完整适配到 OpenAI tool-call 消息，并把每次压缩事件输出到活动流 |
| s09 Memory | 选择/召回/提取/整理 | `memory.py::MemoryStore/MemoryManager` | 使用 `.memory/*.md` 和索引；运行前选择召回，完成后提取并按阈值整理 |
| s10 Task System | 文件任务图 | `_todo_write`、GUI `TODO` 活动 | 单人短任务用显式 Todo；持久 DAG 仍直接读原章 |
| s11 Background | `BackgroundManager` | `qt_gui.py` 工作线程；原章 | GUI 不阻塞；通用后台命令直接读原章 |
| s12 Cron | durable cron queue | `s12_cron_scheduler/code.py` | 不在即时 coding 默认链，直接复用原章 |
| s13 Agent Teams | MessageBus/Task/worktree/protocol | `s13_agent_teams/code.py` | 不在单人默认链，直接复用原章 |
| s14 MCP | late-bound prefixed tools | `s14_mcp_plugin/code.py` | 教学 Mock MCP 不冒充真实 MCP，直接复用原章 |
| s15 Integrated | 多机制一个 loop | `CodingAgent` 整体 | 结构适配 |
| s16 Workflow | trusted workflow + journal/resume | 固定 `verify` 工具与宿主 gate；原章 | 复用“模型选择、宿主执行”的信任边界 |
| s17 Goal Loop | Stop hook + evaluator | `CodingAgent.run` 的 Stop Gate | 用确定性“修改后验证”条件适配，避免模型判断冒充测试 |

百炼接入是必要的协议适配，不是新增 Agent 框架：`agent.py::_load_live_client` 使用 OpenAI 兼容入口，核心 Harness 机制仍限定在 s01–s17。
