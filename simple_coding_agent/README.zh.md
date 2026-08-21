# Simple Bailian Coding Agent

这是一个能直接处理小型代码任务的单 Agent：选择工作区，输入任务，模型会查看文件、修改代码、运行验证，并在窗口中显示全过程。模型使用阿里云百炼 OpenAI 兼容接口；Harness 机制来自 [learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 的 s01–s17，没有引入 LangChain、LangGraph、RAG 或新的 Agent 框架。

## 界面效果

![Bailian Code 浅色 Qt 工作台](docs/images/bailian-code-light.png)

> 本图来自 macOS 上实际启动的 PySide6/Qt 应用窗口，不是网页或设计稿。

## 1. 最快启动

建议使用 Conda `bailian-code` 环境（Python 3.12）。GUI 基于 PySide6/Qt，是原生桌面窗口，不启动本地网页或浏览器。

```bash
cd bailian-coding-agent
conda run -n bailian-code python -m pip install -r requirements.txt
conda run -n bailian-code python -m simple_coding_agent
```

不传任务时默认打开窗口。窗口中：

1. 选择要修改的代码工作区；
2. 输入百炼模型 ID，默认 `qwen3-coder-plus`；
3. 输入明确任务；
4. 点击“运行”；
5. Agent 请求 shell、测试命令或覆盖已有文件时逐条批准。也可勾选自动批准；硬拒绝规则始终生效。

Qt 工作台采用成熟 Coding Agent 常见的任务优先结构：左侧固定项目、模型和安全设置；中央显示任务对话与执行时间线；右侧独立展示 Plan、Subagent 和真实变更文件；底部任务输入框始终可用。视觉使用暖灰画布、白色信息面板、低对比边界、单一灰蓝交互强调和语义状态色，避免“配置表单 + 原始日志”的后台工具感。快捷键为 `Command+Enter`（Windows/Linux 使用 `Ctrl+Enter`）运行、`Command+K` 新建任务、`Esc` 请求停止。

Key 只从环境变量或 `.env` 读取，不会显示在窗口或写入代码：

```bash
export DASHSCOPE_API_KEY="你的百炼 API Key"
```

可选变量为 `BAILIAN_MODEL` 和 `BAILIAN_BASE_URL`。中国内地公共兼容地址默认为 `https://dashscope.aliyuncs.com/compatible-mode/v1`。

## 2. 命令行用法

一次性任务：

```bash
conda run -n bailian-code python -m simple_coding_agent \
  --workspace /absolute/path/to/project \
  --yes \
  "检查失败测试，修复根因并运行相关测试"
```

连续终端对话：

```bash
conda run -n bailian-code python -m simple_coding_agent \
  --cli --workspace /absolute/path/to/project
```

终端模式支持 `/reset`、`/help`、`/exit`。

## 3. 实际执行闭环

```text
用户任务
   ↓
百炼模型决定：继续调用工具，还是给出最终答案
   ↓ 调用工具
Hooks/权限 → 文件或命令工具 → 真实结果写回 messages[]
   ↑                                      ↓
   └──────────────── 继续推理 ────────────┘
   ↓ 模型想停止
若最后一次修改之后没有成功 verify，Stop Gate 拒绝结束
```

可用工具：

| 工具 | 用途 |
|---|---|
| `read_file` | 按带行号的范围读取 UTF-8 文本 |
| `glob` | 在工作区内查找路径 |
| `search_text` | 安全地跨文件搜索文本，并返回文件、行号和匹配行 |
| `write_file` | 创建文件；默认拒绝覆盖，显式覆盖必须经宿主审批 |
| `edit_file` | 唯一匹配后精确替换 |
| `bash` | 执行查看、搜索等命令 |
| `verify` | 运行测试、构建、Lint 或语法检查并记录退出码 |
| `todo_write` | 更新多步骤任务的短计划 |
| `task` | 用全新上下文启动只读研究子 Agent |
| `load_skill` | 按需读取现有 `skills/*/SKILL.md` |
| `compact` | 显式归档并摘要早期对话，释放上下文空间 |

### 记忆机制

运行前，Agent 会根据当前请求从工作区 `.memory/` 中选择最多 5 条相关记录并注入系统上下文；任务完成后会调用无工具的辅助模型，从最近对话中提取稳定的用户偏好、项目事实、反馈或参考资料。临时任务状态不会写入长期记忆。记忆达到 10 条后会尝试去重、合并和整理，并在失败时恢复原文件。

### 上下文压缩

每次主模型调用前依次执行：大工具结果落盘、旧消息归档、旧工具结果微压缩、超限后的模型摘要。模型也可以调用 `compact` 主动压缩；若百炼返回上下文过长错误，则保留最近消息进行一次反应式压缩后重试。完整记录保存在 `.transcripts/`，超大工具输出保存在 `.task_outputs/tool-results/`，每一步都会以 `CONTEXT` 事件显示在 GUI。

### Subagent 与 Todo

`task` 会创建带唯一 ID 的只读研究 Subagent，拥有独立上下文以及 `read_file`、`glob`、`search_text`、`load_skill` 四个工具。创建、内部工具事件和完成状态都会显示在 GUI。`todo_write` 的计划摘要和每个步骤也会以 `TODO` 事件显示。

## 4. 与 s01–s17 的关系

详细复用表见 [REUSE_MAP.zh.md](REUSE_MAP.zh.md)，代码中的 `REUSE[sXX]` 注释可直接搜索。表内的课程源码路径指向上游 `learn-claude-code` 仓库；本独立仓库只保留运行所需代码和 `agent-builder` skill。

这里必须区分两个概念：

- **知识点完整**：s01–s17 每一章都有真实源码入口、用途和边界说明；
- **默认运行路径最小**：只启用即时单人 coding 直接需要的机制。

课程自己也规定 s15 是 s01–s15 的累计集成；s16 和 s17 是聚焦机制示例，不是继续叠加后的“大一统版本”。因此，本应用不会复制一套 Cron、持久团队、Mock MCP 或通用 Workflow Runtime。直接复用原章比复制后形成两套相似代码更容易学习，也避免把教学机制误当成生产能力。

## 5. 安全边界

- 文件工具使用解析后的绝对路径，不能越过所选工作区；
- `write_file` 默认拒绝已有文件；应优先使用 `edit_file`，完整覆盖需要 `overwrite=true` 和审批；
- `rm -rf /`、`sudo`、`git reset --hard` 等硬拒绝模式不会执行；
- 普通 shell 命令默认逐条审批；
- 文件发生修改后，必须有一次退出码为 0 的 `verify`，否则 Agent 不能声明完成；
- 模型调用最多 20 轮，命令默认超时 120 秒，工具输出超过 20,000 字符会截断；
- “停止”会在当前 API 调用或命令返回后的边界生效。

这不是操作系统沙箱。shell 仍具有当前用户权限；自动批准模式应只在 Git 工作区或一次性目录中使用。Worktree 也只是 checkout/branch 隔离，不是安全沙箱。

## 6. 测试

不调用 API 的确定性测试：

```bash
conda run -n bailian-code python -m unittest -v \
  simple_coding_agent.test_agent \
  simple_coding_agent.test_qt_gui \
  simple_coding_agent.test_runtime_features \
  examples.knapsack.test_knapsack_problem
```

语法检查：

```bash
conda run -n bailian-code python -m py_compile \
  simple_coding_agent/agent.py \
  simple_coding_agent/gui_events.py \
  simple_coding_agent/qt_gui.py \
  simple_coding_agent/course_map.py
```

`demo_project/` 的两个 `.fixture` 文件包含一个故意写错的减法函数，供真实百炼 E2E 使用。测试时应复制到一次性目录并去掉 `.fixture` 后缀，避免把 Agent 的修改混入教材。
