"""Qt desktop workbench for :mod:`simple_coding_agent.agent`.

The runtime remains the same Python coding agent.  Qt provides the presentation
layer needed for a task-first, native desktop interface without a browser.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .agent import AgentError, CodingAgent, _load_live_client
from .gui_events import (
    SIDEBAR_ONLY_ACTIVITY,
    classify_activity,
    compact_path,
    parse_subagent_event,
    parse_todo_event,
)


APP_STYLE_TEMPLATE = """
* {
    color: #ECEEF1;
    font-family: "SF Pro Text", "Segoe UI", sans-serif;
    font-size: 13px;
}
QMainWindow, QWidget#root, QWidget#centre, QScrollArea, QWidget#feedHost {
    background: #101214;
}
QWidget#leftRail, QWidget#inspector {
    background: #15181B;
}
QWidget#leftRail { border-right: 1px solid #2A2F36; }
QWidget#inspector { border-left: 1px solid #2A2F36; }
QFrame#topbar {
    background: #121416;
    border-bottom: 1px solid #22262C;
}
QFrame#card, QFrame#contextCard, QFrame#runCard {
    background: #191C20;
    border: 1px solid #272C33;
    border-radius: 8px;
}
QFrame#composer {
    background: #191C20;
    border: 1px solid #343A43;
    border-radius: 10px;
}
QFrame#composer[focused="true"] { border-color: #526784; }
QLabel#brandMark {
    min-width: 34px; max-width: 34px;
    min-height: 34px; max-height: 34px;
    color: #8FA8CE;
    background: #253044;
    border: 1px solid #34445E;
    font-size: 19px;
    font-weight: 700;
}
QLabel#brandName { font-size: 15px; font-weight: 700; }
QLabel[role="eyebrow"] {
    color: #707985;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel[role="muted"] { color: #A2A9B3; }
QLabel[role="faint"] { color: #707985; }
QLabel#projectName { font-size: 12px; font-weight: 650; }
QLabel#mono, QLabel[role="mono"] {
    color: #707985;
    font-family: Menlo, monospace;
    font-size: 9px;
}
QPushButton {
    border: 0;
    border-radius: 6px;
    padding: 8px 10px;
    background: #20242A;
}
QPushButton:hover { background: #272C33; }
QPushButton:pressed { background: #2B3139; }
QPushButton#newTask {
    padding: 10px 12px;
    text-align: left;
    font-weight: 650;
}
QPushButton#ghostButton {
    color: #A2A9B3;
    background: transparent;
    border: 1px solid #2A2F36;
}
QPushButton#primaryButton {
    color: #F8F9FB;
    background: #7392C3;
    padding: 9px 14px;
    font-weight: 700;
}
QPushButton#primaryButton:hover { background: #82A0D0; }
QPushButton#primaryButton:disabled { color: #707985; background: #2A2F36; }
QPushButton#stopButton {
    color: #D4878C;
    background: #3B2529;
    min-width: 34px; max-width: 34px;
}
QPushButton#stopButton:disabled { color: #4D5259; background: #1C1F23; }
QPushButton#starter {
    min-height: 58px;
    padding: 10px 12px;
    color: #A2A9B3;
    background: #171A1E;
    border: 1px solid #2A2F36;
    text-align: left;
}
QPushButton#starter:hover { color: #ECEEF1; border-color: #3C4654; background: #20242A; }
QLineEdit, QTextEdit {
    color: #ECEEF1;
    background: #111315;
    border: 1px solid #2A2F36;
    border-radius: 6px;
    selection-background-color: #334661;
}
QLineEdit { padding: 7px 8px; font-family: Menlo, monospace; font-size: 10px; }
QLineEdit:focus, QTextEdit:focus { border-color: #526784; }
QTextEdit#prompt {
    background: transparent;
    border: 0;
    padding: 4px;
    font-size: 13px;
}
QCheckBox { color: #A2A9B3; spacing: 7px; }
QCheckBox::indicator {
    width: 28px; height: 16px;
    border: 1px solid #353B43;
    border-radius: 8px;
    background: #252A30;
}
QCheckBox::indicator:checked { background: #5878AA; border-color: #6F8EBE; }
QLabel#pill {
    padding: 5px 8px;
    color: #A2A9B3;
    background: #191C20;
    border: 1px solid #2A2F36;
    border-radius: 5px;
    font-size: 9px;
}
QLabel#statusPill[state="ready"], QLabel#statusPill[state="complete"] {
    color: #82B691; background: #203128; border: 1px solid #2E4938;
}
QLabel#statusPill[state="running"] {
    color: #8FA8CE; background: #253044; border: 1px solid #34435A;
}
QLabel#statusPill[state="warning"] {
    color: #D1A66B; background: #382E20; border: 1px solid #4D3D28;
}
QLabel#statusPill[state="error"] {
    color: #D4878C; background: #3B2529; border: 1px solid #503137;
}
QLabel#taskTitle { font-size: 21px; font-weight: 680; }
QLabel#welcomeTitle { font-size: 24px; font-weight: 650; }
QLabel#welcomeMark {
    min-width: 58px; max-width: 58px;
    min-height: 58px; max-height: 58px;
    color: #8FA8CE;
    border: 1px solid #2A2F36;
    border-radius: 29px;
    font-size: 26px;
}
QFrame#activityItem {
    background: transparent;
    border-left: 1px solid #2A2F36;
}
QLabel#activityDot {
    min-width: 8px; max-width: 8px;
    min-height: 8px; max-height: 8px;
    border-radius: 4px;
    background: #707985;
}
QLabel#activityDot[kind="user"], QLabel#activityDot[kind="tool"] { background: #8FA8CE; }
QLabel#activityDot[kind="result"], QLabel#activityDot[kind="success"] { background: #82B691; }
QLabel#activityDot[kind="warning"] { background: #D1A66B; }
QLabel#activityDot[kind="error"] { background: #D4878C; }
QLabel#activityLabel { color: #707985; font-size: 9px; font-weight: 700; letter-spacing: 1px; }
QLabel#activityLabel[kind="tool"] { color: #8FA8CE; }
QLabel#activityLabel[kind="success"], QLabel#activityLabel[kind="result"] { color: #82B691; }
QLabel#activityLabel[kind="warning"] { color: #D1A66B; }
QLabel#activityLabel[kind="error"] { color: #D4878C; }
QLabel#activityBody { color: #A2A9B3; font-family: Menlo, monospace; font-size: 10px; }
QLabel#activityBody[kind="user"] {
    padding: 11px 13px;
    color: #ECEEF1;
    background: #253044;
    border: 1px solid #303B4C;
    border-radius: 7px;
    font-family: "SF Pro Text";
    font-size: 12px;
}
QLabel#activityBody[kind="result"] { color: #ECEEF1; font-family: "SF Pro Text"; font-size: 12px; }
QLabel#contextTitle { color: #A2A9B3; font-size: 10px; font-weight: 600; }
QLabel#contextDetail { color: #707985; font-family: Menlo, monospace; font-size: 8px; }
QLabel#contextDot {
    min-width: 7px; max-width: 7px;
    min-height: 7px; max-height: 7px;
    border: 1px solid #707985;
    border-radius: 4px;
}
QLabel#contextDot[state="in_progress"], QLabel#contextDot[state="running"] { background: #8FA8CE; border-color: #8FA8CE; }
QLabel#contextDot[state="completed"] { background: #82B691; border-color: #82B691; }
QLabel#contextDot[state="failed"] { background: #D4878C; border-color: #D4878C; }
QLabel#contextDot[state="changed"] { background: #D1A66B; border-color: #D1A66B; border-radius: 1px; }
QScrollBar:vertical { width: 8px; background: transparent; margin: 3px 0; }
QScrollBar::handle:vertical { min-height: 30px; border-radius: 4px; background: #30353C; }
QScrollBar::handle:vertical:hover { background: #414851; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QDialog#approvalDialog { background: #191C20; }
"""

# Keep all widget rules in one stylesheet while projecting them onto a warm,
# low-glare light palette.  Semantic hues remain darker than their fills so
# status meaning survives without high saturation.
LIGHT_PALETTE = {
    "#ECEEF1": "#20252B",
    "#101214": "#F7F8FA",
    "#15181B": "#EFF1F3",
    "#2A2F36": "#D9DEE5",
    "#121416": "#FFFFFF",
    "#22262C": "#E7EAEE",
    "#191C20": "#FFFFFF",
    "#272C33": "#DDE1E6",
    "#343A43": "#D2D8E0",
    "#526784": "#6C88AE",
    "#8FA8CE": "#607EA6",
    "#253044": "#E8EEF5",
    "#34445E": "#C7D3E2",
    "#707985": "#8A949F",
    "#A2A9B3": "#606A75",
    "#20242A": "#F5F6F8",
    "#2B3139": "#E6E9ED",
    "#7392C3": "#607FA8",
    "#82A0D0": "#6C89AF",
    "#3B2529": "#F6E9EA",
    "#D4878C": "#AD6568",
    "#4D5259": "#B9BFC7",
    "#1C1F23": "#ECEFF2",
    "#171A1E": "#FFFFFF",
    "#3C4654": "#BBC6D3",
    "#111315": "#F7F8FA",
    "#5878AA": "#6E88AC",
    "#6F8EBE": "#607FA8",
    "#353B43": "#CDD2D9",
    "#252A30": "#E1E5EA",
    "#82B691": "#5F8A70",
    "#203128": "#E8F2EC",
    "#2E4938": "#CDE1D4",
    "#D1A66B": "#A27945",
    "#382E20": "#F5EFE5",
    "#4D3D28": "#E7D8C3",
    "#503137": "#E7CBCD",
    "#303B4C": "#CFD9E6",
    "#30353C": "#CED3D9",
    "#414851": "#B8C0C9",
}
APP_STYLE = APP_STYLE_TEMPLATE
for _dark_color, _light_color in LIGHT_PALETTE.items():
    APP_STYLE = APP_STYLE.replace(_dark_color, _light_color)


def clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


class EventBridge(QObject):
    log = Signal(str)
    result = Signal(object)
    failure = Signal(object)
    done = Signal()
    approval = Signal(str, str)


class ActivityItem(QFrame):
    LABELS = {
        "user": "YOU",
        "result": "AGENT",
        "tool": "TOOL CALL",
        "tool_result": "TOOL RESULT",
        "memory": "MEMORY",
        "success": "VERIFIED",
        "warning": "CONTEXT",
        "error": "ERROR",
        "meta": "SYSTEM",
    }

    def __init__(self, kind: str, text: str) -> None:
        super().__init__()
        self.setObjectName("activityItem")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 18)
        layout.setSpacing(14)

        marker_column = QVBoxLayout()
        marker_column.setContentsMargins(0, 4, 0, 0)
        dot = QLabel()
        dot.setObjectName("activityDot")
        dot.setProperty("kind", kind)
        marker_column.addWidget(dot, 0, Qt.AlignmentFlag.AlignHCenter)
        marker_column.addStretch()
        layout.addLayout(marker_column)

        content = QVBoxLayout()
        content.setSpacing(7)
        label = QLabel(self.LABELS.get(kind, "SYSTEM"))
        label.setObjectName("activityLabel")
        label.setProperty("kind", kind)
        body = QLabel(text.strip())
        body.setObjectName("activityBody")
        body.setProperty("kind", kind)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content.addWidget(label)
        content.addWidget(body)
        layout.addLayout(content, 1)


class ContextPanel(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        heading = QHBoxLayout()
        label = QLabel(title)
        label.setProperty("role", "eyebrow")
        self.count = QLabel("0")
        self.count.setProperty("role", "mono")
        heading.addWidget(label)
        heading.addStretch()
        heading.addWidget(self.count)
        outer.addLayout(heading)

        self.card = QFrame()
        self.card.setObjectName("contextCard")
        self.rows = QVBoxLayout(self.card)
        self.rows.setContentsMargins(10, 9, 10, 9)
        self.rows.setSpacing(9)
        outer.addWidget(self.card)

    def render(
        self,
        rows: list[tuple[str, str, str]],
        *,
        empty: str,
        count: str,
    ) -> None:
        clear_layout(self.rows)
        self.count.setText(count)
        if not rows:
            row = QHBoxLayout()
            dot = QLabel()
            dot.setObjectName("contextDot")
            text = QLabel(empty)
            text.setProperty("role", "faint")
            text.setWordWrap(True)
            row.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(text, 1)
            self.rows.addLayout(row)
            return
        for state, title, detail in rows:
            row = QHBoxLayout()
            row.setSpacing(8)
            dot = QLabel()
            dot.setObjectName("contextDot")
            dot.setProperty("state", state)
            copy = QVBoxLayout()
            copy.setSpacing(2)
            title_label = QLabel(title)
            title_label.setObjectName("contextTitle")
            title_label.setWordWrap(True)
            detail_label = QLabel(detail)
            detail_label.setObjectName("contextDetail")
            detail_label.setWordWrap(True)
            copy.addWidget(title_label)
            if detail:
                copy.addWidget(detail_label)
            row.addWidget(dot, 0, Qt.AlignmentFlag.AlignTop)
            row.addLayout(copy, 1)
            self.rows.addLayout(row)


class ApprovalDialog(QDialog):
    def __init__(self, parent: QWidget, action: str) -> None:
        super().__init__(parent)
        self.setObjectName("approvalDialog")
        self.setWindowTitle("操作审批")
        self.setModal(True)
        self.resize(560, 330)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        eyebrow = QLabel("HOST APPROVAL")
        eyebrow.setProperty("role", "eyebrow")
        title = QLabel("Agent 请求执行操作")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        body = QLabel("确认命令和目标路径在当前任务范围内。拒绝后 Agent 会收到失败结果。")
        body.setProperty("role", "muted")
        body.setWordWrap(True)
        action_box = QTextEdit(action)
        action_box.setReadOnly(True)
        action_box.setMinimumHeight(145)
        buttons = QHBoxLayout()
        deny = QPushButton("拒绝")
        deny.setObjectName("ghostButton")
        allow = QPushButton("允许一次")
        allow.setObjectName("primaryButton")
        deny.clicked.connect(self.reject)
        allow.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(deny)
        buttons.addWidget(allow)
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(action_box, 1)
        layout.addLayout(buttons)


class CodingAgentWindow(QMainWindow):
    def __init__(
        self,
        *,
        initial_workspace: Path,
        initial_model: str,
        base_url: str,
        max_turns: int,
        command_timeout: int,
        enable_thinking: bool,
    ) -> None:
        super().__init__()
        self.base_url = base_url
        self.max_turns = max_turns
        self.command_timeout = command_timeout
        self.enable_thinking = enable_thinking
        self.agent: CodingAgent | None = None
        self.agent_identity: tuple[Path, str, bool] | None = None
        self.worker: threading.Thread | None = None
        self.cancel_event = threading.Event()
        self.started_at: float | None = None
        self._approval_requests: dict[str, tuple[dict[str, bool], threading.Event]] = {}
        self._todo_items: dict[int, dict[str, str]] = {}
        self._todo_total = 0
        self._todo_completed = 0
        self._subagent_items: dict[str, dict[str, str]] = {}
        self._changed_files: tuple[str, ...] = ()
        self._activity_count = 0

        self.bridge = EventBridge()
        self.bridge.log.connect(self._append_log)
        self.bridge.result.connect(self._handle_result)
        self.bridge.failure.connect(self._handle_failure)
        self.bridge.done.connect(self._handle_done)
        self.bridge.approval.connect(self._show_approval)

        self.setWindowTitle("Bailian Code")
        self.resize(1380, 860)
        self.setMinimumSize(1120, 720)
        self._build_ui(initial_workspace.resolve(), initial_model)
        self._connect_shortcuts()

        self.clock = QTimer(self)
        self.clock.timeout.connect(self._refresh_clock)
        self.clock.start(1000)

    def _build_ui(self, workspace: Path, model: str) -> None:
        root = QWidget()
        root.setObjectName("root")
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        shell.addWidget(self._build_left_rail(workspace, model))
        shell.addWidget(self._build_centre(), 1)
        shell.addWidget(self._build_inspector())
        self.setCentralWidget(root)
        self._refresh_project_labels()
        self._render_runtime_panels()

    def _build_left_rail(self, workspace: Path, model: str) -> QWidget:
        rail = QWidget()
        rail.setObjectName("leftRail")
        rail.setFixedWidth(240)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(0)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        mark = QLabel("⌁")
        mark.setObjectName("brandMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(1)
        name = QLabel("Bailian")
        name.setObjectName("brandName")
        product = QLabel("CODE AGENT")
        product.setProperty("role", "eyebrow")
        brand_copy.addWidget(name)
        brand_copy.addWidget(product)
        brand.addWidget(mark)
        brand.addLayout(brand_copy)
        brand.addStretch()
        layout.addLayout(brand)
        layout.addSpacing(18)

        new_task = QPushButton("＋   新建任务                                      ⌘ K")
        new_task.setObjectName("newTask")
        new_task.clicked.connect(self._reset)
        layout.addWidget(new_task)
        layout.addSpacing(22)

        layout.addWidget(self._eyebrow("PROJECT"))
        layout.addSpacing(7)
        project = QFrame()
        project.setObjectName("card")
        project_layout = QHBoxLayout(project)
        project_layout.setContentsMargins(10, 10, 8, 10)
        project_layout.setSpacing(9)
        folder = QLabel("▰")
        folder.setStyleSheet("color: #607EA6; font-size: 14px;")
        copy = QVBoxLayout()
        copy.setSpacing(3)
        self.project_name = QLabel()
        self.project_name.setObjectName("projectName")
        self.project_path = QLabel()
        self.project_path.setObjectName("mono")
        copy.addWidget(self.project_name)
        copy.addWidget(self.project_path)
        choose = QPushButton("···")
        choose.setFixedWidth(31)
        choose.clicked.connect(self._choose_workspace)
        project_layout.addWidget(folder)
        project_layout.addLayout(copy, 1)
        project_layout.addWidget(choose)
        layout.addWidget(project)
        layout.addSpacing(20)

        layout.addWidget(self._eyebrow("MODEL & SAFETY"))
        layout.addSpacing(7)
        settings = QFrame()
        settings.setObjectName("card")
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(7)
        model_label = QLabel("BAILIAN MODEL")
        model_label.setProperty("role", "eyebrow")
        self.model_input = QLineEdit(model)
        self.model_input.setPlaceholderText("Model ID")
        self.workspace_input = QLineEdit(str(workspace))
        self.workspace_input.hide()
        safety_row = QHBoxLayout()
        safety_copy = QVBoxLayout()
        safety_copy.setSpacing(1)
        protected = QLabel("逐次审批")
        protected.setObjectName("projectName")
        safety_note = QLabel("硬拒绝规则始终生效")
        safety_note.setProperty("role", "faint")
        self.auto_approve = QCheckBox()
        self.auto_approve.setToolTip("自动批准普通命令和显式覆盖")
        safety_copy.addWidget(protected)
        safety_copy.addWidget(safety_note)
        safety_row.addLayout(safety_copy, 1)
        safety_row.addWidget(self.auto_approve)
        settings_layout.addWidget(model_label)
        settings_layout.addWidget(self.model_input)
        settings_layout.addSpacing(3)
        settings_layout.addLayout(safety_row)
        layout.addWidget(settings)
        layout.addStretch()

        runtime = QFrame()
        runtime.setObjectName("card")
        runtime_layout = QVBoxLayout(runtime)
        runtime_layout.setContentsMargins(10, 9, 10, 9)
        runtime_layout.setSpacing(5)
        live = QLabel("●  LOCAL RUNTIME")
        live.setStyleSheet("color: #5F8A70; font-size: 9px; font-weight: 700;")
        runtime_layout.addWidget(live)
        for key, value in (
            ("Tools", "11"),
            ("Max turns", str(self.max_turns)),
            ("Timeout", f"{self.command_timeout}s"),
        ):
            row = QHBoxLayout()
            left = QLabel(key)
            left.setProperty("role", "mono")
            right = QLabel(value)
            right.setProperty("role", "mono")
            row.addWidget(left)
            row.addStretch()
            row.addWidget(right)
            runtime_layout.addLayout(row)
        layout.addWidget(runtime)
        layout.addSpacing(7)
        clear = QPushButton("清空活动")
        clear.setObjectName("ghostButton")
        clear.clicked.connect(self._clear_activity)
        layout.addWidget(clear)
        return rail

    def _build_centre(self) -> QWidget:
        centre = QWidget()
        centre.setObjectName("centre")
        layout = QVBoxLayout(centre)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(59)
        top = QHBoxLayout(topbar)
        top.setContentsMargins(22, 0, 22, 0)
        top.setSpacing(8)
        self.breadcrumb_project = QLabel()
        self.breadcrumb_project.setProperty("role", "faint")
        slash = QLabel("/")
        slash.setProperty("role", "faint")
        active = QLabel("active task")
        active.setProperty("role", "muted")
        self.model_pill = QLabel()
        self.model_pill.setObjectName("pill")
        self.status_pill = QLabel("●  就绪")
        self.status_pill.setObjectName("statusPill")
        self.status_pill.setProperty("state", "ready")
        top.addWidget(self.breadcrumb_project)
        top.addWidget(slash)
        top.addWidget(active)
        top.addStretch()
        top.addWidget(self.model_pill)
        top.addWidget(self.status_pill)
        layout.addWidget(topbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        feed_host = QWidget()
        feed_host.setObjectName("feedHost")
        self.feed_layout = QVBoxLayout(feed_host)
        self.feed_layout.setContentsMargins(38, 30, 38, 22)
        self.feed_layout.setSpacing(0)
        heading = QHBoxLayout()
        title_copy = QVBoxLayout()
        title_copy.setSpacing(5)
        title_copy.addWidget(self._eyebrow("TASK ACTIVITY"))
        self.task_title = QLabel("开始一个 coding task")
        self.task_title.setObjectName("taskTitle")
        title_copy.addWidget(self.task_title)
        self.elapsed = QLabel("00:00")
        self.elapsed.setProperty("role", "mono")
        heading.addLayout(title_copy)
        heading.addStretch()
        heading.addWidget(self.elapsed, 0, Qt.AlignmentFlag.AlignBottom)
        self.feed_layout.addLayout(heading)
        self.feed_layout.addSpacing(30)
        self.welcome = self._build_welcome()
        self.feed_layout.addWidget(self.welcome)
        self.feed_layout.addStretch()
        self.scroll.setWidget(feed_host)
        layout.addWidget(self.scroll, 1)

        composer_wrap = QWidget()
        composer_layout = QVBoxLayout(composer_wrap)
        composer_layout.setContentsMargins(22, 0, 22, 20)
        self.composer = QFrame()
        self.composer.setObjectName("composer")
        compose = QVBoxLayout(self.composer)
        compose.setContentsMargins(11, 9, 10, 9)
        compose.setSpacing(4)
        self.prompt = QTextEdit()
        self.prompt.setObjectName("prompt")
        self.prompt.setPlaceholderText("描述任务、约束和验收条件…")
        self.prompt.setFixedHeight(72)
        self.prompt.textChanged.connect(self._update_prompt_count)
        footer = QHBoxLayout()
        mode = QLabel("AGENT")
        mode.setObjectName("pill")
        protected = QLabel("Protected  ·  ⌘↵ 运行  ·  Esc 停止")
        protected.setProperty("role", "faint")
        self.prompt_count = QLabel("0")
        self.prompt_count.setProperty("role", "mono")
        self.stop_button = QPushButton("■")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop_run)
        self.run_button = QPushButton("运行任务   ↗")
        self.run_button.setObjectName("primaryButton")
        self.run_button.clicked.connect(self._start_run)
        footer.addWidget(mode)
        footer.addWidget(protected)
        footer.addStretch()
        footer.addWidget(self.prompt_count)
        footer.addWidget(self.stop_button)
        footer.addWidget(self.run_button)
        compose.addWidget(self.prompt)
        compose.addLayout(footer)
        composer_layout.addWidget(self.composer)
        layout.addWidget(composer_wrap)
        return centre

    def _build_welcome(self) -> QWidget:
        welcome = QWidget()
        layout = QVBoxLayout(welcome)
        layout.setContentsMargins(50, 45, 50, 35)
        layout.setSpacing(8)
        mark = QLabel("◇")
        mark.setObjectName("welcomeMark")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("What should we build?")
        title.setObjectName("welcomeTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel("描述目标与验收条件。Agent 会探索工作区、执行工具、修改文件并运行验证。")
        body.setProperty("role", "muted")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mark, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(8)
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addSpacing(20)
        starters = QHBoxLayout()
        starters.setSpacing(9)
        prompts = (
            ("01  修复失败测试\n定位根因并验证", "检查当前项目的失败测试，定位根因、修复并运行相关验证。"),
            ("02  审查当前实现\n优先处理高风险问题", "审查当前实现，找出最重要的可靠性问题并提出最小修复。"),
            ("03  解释调用链\n基于实际源码", "解释当前项目的一条真实调用链，列出关键函数和运行边界。"),
        )
        for label, prompt in prompts:
            button = QPushButton(label)
            button.setObjectName("starter")
            button.clicked.connect(lambda _checked=False, value=prompt: self._use_prompt(value))
            starters.addWidget(button, 1)
        layout.addLayout(starters)
        return welcome

    def _build_inspector(self) -> QWidget:
        inspector = QWidget()
        inspector.setObjectName("inspector")
        inspector.setFixedWidth(292)
        layout = QVBoxLayout(inspector)
        layout.setContentsMargins(13, 0, 13, 16)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)
        label = self._eyebrow("TASK CONTEXT")
        live = QLabel("LIVE")
        live.setStyleSheet("color: #5F8A70; background: #E8F2EC; padding: 4px 7px; font-size: 8px; font-weight: 700;")
        header.addWidget(label)
        header.addStretch()
        header.addWidget(live)
        header_host = QWidget()
        header_host.setFixedHeight(59)
        header_host.setLayout(header)
        layout.addWidget(header_host)

        run_card = QFrame()
        run_card.setObjectName("runCard")
        run_layout = QVBoxLayout(run_card)
        run_layout.setContentsMargins(12, 12, 12, 12)
        run_layout.setSpacing(5)
        icon_row = QHBoxLayout()
        icon = QLabel("⌁")
        icon.setStyleSheet("color: #607EA6; font-size: 20px;")
        self.run_status_dot = QLabel("●")
        self.run_status_dot.setStyleSheet("color: #5F8A70;")
        icon_row.addWidget(icon)
        icon_row.addStretch()
        icon_row.addWidget(self.run_status_dot)
        self.run_state_title = QLabel("Ready")
        self.run_state_title.setObjectName("projectName")
        self.run_meta = QLabel("Ready for a new task")
        self.run_meta.setProperty("role", "muted")
        self.run_meta.setWordWrap(True)
        run_layout.addLayout(icon_row)
        run_layout.addSpacing(7)
        run_layout.addWidget(self.run_state_title)
        run_layout.addWidget(self.run_meta)
        layout.addSpacing(14)
        layout.addWidget(run_card)
        layout.addSpacing(18)

        self.plan_panel = ContextPanel("PLAN")
        self.subagent_panel = ContextPanel("DELEGATION")
        self.changes_panel = ContextPanel("CHANGES")
        layout.addWidget(self.plan_panel)
        layout.addSpacing(17)
        layout.addWidget(self.subagent_panel)
        layout.addSpacing(17)
        layout.addWidget(self.changes_panel)
        layout.addStretch()
        return inspector

    @staticmethod
    def _eyebrow(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("role", "eyebrow")
        return label

    def _connect_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._start_run)
        QShortcut(QKeySequence("Meta+Return"), self, activated=self._start_run)
        QShortcut(QKeySequence("Escape"), self, activated=self._stop_run)
        QShortcut(QKeySequence("Meta+K"), self, activated=self._reset)

    def _choose_workspace(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "选择代码工作区", self.workspace_input.text()
        )
        if selected:
            self.workspace_input.setText(selected)
            self._refresh_project_labels()

    def _refresh_project_labels(self) -> None:
        path = Path(self.workspace_input.text()).expanduser()
        self.project_name.setText(path.name or str(path))
        self.project_path.setText(compact_path(str(path), 29))
        self.project_path.setToolTip(str(path))
        self.breadcrumb_project.setText(path.name or "workspace")
        model = self.model_input.text().strip() or "No model"
        self.model_pill.setText(model)

    def _use_prompt(self, prompt: str) -> None:
        self.prompt.setPlainText(prompt)
        self.prompt.setFocus()

    def _update_prompt_count(self) -> None:
        self.prompt_count.setText(str(len(self.prompt.toPlainText().strip())))

    def _start_run(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        goal = self.prompt.toPlainText().strip()
        workspace = Path(self.workspace_input.text()).expanduser().resolve()
        model = self.model_input.text().strip()
        if not goal:
            QMessageBox.warning(self, "任务为空", "请输入一个明确的 coding 任务。")
            return
        if not workspace.is_dir():
            QMessageBox.warning(self, "工作区无效", f"目录不存在：{workspace}")
            return
        if not model:
            QMessageBox.warning(self, "模型为空", "请输入百炼模型 ID。")
            return

        identity = (workspace, model, self.auto_approve.isChecked())
        self.cancel_event.clear()
        self.started_at = time.monotonic()
        self._reset_runtime_panels()
        self._refresh_project_labels()
        self._append_entry("user", goal)
        self.task_title.setText(goal.splitlines()[0][:70])
        self.prompt.clear()
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._set_status("running", "运行中")
        self.run_state_title.setText("Working")
        self.run_meta.setText(f"Exploring {workspace.name}")
        self.worker = threading.Thread(
            target=self._run_worker,
            args=(goal, identity),
            daemon=True,
            name="coding-agent-qt-worker",
        )
        self.worker.start()

    def _run_worker(self, goal: str, identity: tuple[Path, str, bool]) -> None:
        try:
            if self.agent is None or self.agent_identity != identity:
                workspace, model, auto_approve = identity
                client = _load_live_client(self.base_url)
                self.agent = CodingAgent(
                    client=client,
                    model=model,
                    workspace=workspace,
                    approve_shell=auto_approve,
                    max_turns=self.max_turns,
                    command_timeout=self.command_timeout,
                    enable_thinking=self.enable_thinking,
                    log_callback=self.bridge.log.emit,
                    approval_callback=(None if auto_approve else self._ask_approval),
                    cancel_event=self.cancel_event,
                )
                self.agent_identity = identity
            self.bridge.result.emit(self.agent.run(goal))
        except Exception as error:
            self.bridge.failure.emit(error)
        finally:
            self.bridge.done.emit()

    def _ask_approval(self, action: str) -> bool:
        request_id = uuid4().hex[:12]
        answer = {"allow": False}
        finished = threading.Event()
        self._approval_requests[request_id] = (answer, finished)
        self.bridge.approval.emit(request_id, action)
        while not finished.wait(0.1):
            if self.cancel_event.is_set():
                self._approval_requests.pop(request_id, None)
                return False
        self._approval_requests.pop(request_id, None)
        return answer["allow"]

    def _show_approval(self, request_id: str, action: str) -> None:
        request = self._approval_requests.get(request_id)
        if request is None:
            return
        answer, finished = request
        dialog = ApprovalDialog(self, action)
        answer["allow"] = dialog.exec() == QDialog.DialogCode.Accepted
        finished.set()

    def _stop_run(self) -> None:
        if not (self.worker and self.worker.is_alive()):
            return
        self.cancel_event.set()
        self._set_status("warning", "正在停止")
        self.run_state_title.setText("Stopping")
        self.run_meta.setText("将在当前 API / 命令边界生效")

    def _reset(self) -> None:
        if self.worker and self.worker.is_alive():
            QMessageBox.information(self, "仍在运行", "请先停止当前任务。")
            return
        if self.agent is not None:
            self.agent.reset()
        self.agent = None
        self.agent_identity = None
        self.started_at = None
        self.task_title.setText("开始一个 coding task")
        self._set_status("ready", "就绪")
        self.run_state_title.setText("Ready")
        self.run_meta.setText("Ready for a new task")
        self._reset_runtime_panels()
        self._clear_activity()
        self.prompt.setFocus()

    def _clear_activity(self) -> None:
        while self.feed_layout.count() > 4:
            item = self.feed_layout.takeAt(3)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._activity_count = 0
        self.welcome.show()

    def _append_entry(self, kind: str, text: str) -> None:
        if self._activity_count == 0:
            self.welcome.hide()
        item = ActivityItem(kind, text)
        self.feed_layout.insertWidget(self.feed_layout.count() - 1, item)
        self._activity_count += 1
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _append_log(self, line: str) -> None:
        self._consume_runtime_projection(line)
        category = classify_activity(line)
        if category in SIDEBAR_ONLY_ACTIVITY:
            return
        cleaned = line.strip()
        for prefix in (
            "[tool]",
            "[memory]",
            "[stop]",
            "[context]",
            "[workspace]",
            "[error]",
            ">",
        ):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :].strip()
                break
        self._append_entry(category, cleaned)

    def _consume_runtime_projection(self, line: str) -> None:
        todo = parse_todo_event(line)
        if todo is not None:
            if todo["kind"] == "clear":
                self._todo_items.clear()
                self._todo_total = self._todo_completed = 0
            elif todo["kind"] == "summary":
                self._todo_items.clear()
                self._todo_total = todo["total"]
                self._todo_completed = todo["completed"]
            elif todo["kind"] == "item":
                self._todo_items[todo["index"]] = {
                    "status": todo["status"],
                    "content": todo["content"],
                }
                if not self._todo_total:
                    self._todo_total = max(self._todo_items)
                    self._todo_completed = sum(
                        item["status"] == "completed"
                        for item in self._todo_items.values()
                    )
            self._render_runtime_panels()
            return

        subagent = parse_subagent_event(line)
        if subagent is None:
            return
        subagent_id = str(subagent["id"])
        record = self._subagent_items.setdefault(
            subagent_id, {"status": "running", "detail": "正在启动"}
        )
        if subagent["kind"] == "created":
            record.update(
                status="running",
                detail=f"{subagent['mode']} · {subagent['tool_count']} tools",
            )
        elif subagent["kind"] == "tool":
            record.update(status="running", detail=f"调用 {subagent['tool']}")
        elif subagent["kind"] == "completed":
            record.update(
                status="completed",
                detail=f"{subagent['turns']} turns · {subagent['tool_calls']} tools",
            )
        elif subagent["kind"] == "failed":
            record.update(status="failed", detail=subagent["error"][:40])
        self._render_runtime_panels()

    def _render_runtime_panels(self) -> None:
        plan_rows = [
            (item["status"], f"{index}. {item['content']}", "")
            for index, item in sorted(self._todo_items.items())
        ]
        self.plan_panel.render(
            plan_rows,
            empty="等待 Agent 创建计划",
            count=f"{self._todo_completed} / {self._todo_total}",
        )
        subagent_rows = [
            (record["status"], subagent_id, record["detail"])
            for subagent_id, record in list(self._subagent_items.items())[-3:]
        ]
        self.subagent_panel.render(
            subagent_rows,
            empty="暂无只读研究任务",
            count=str(len(self._subagent_items)),
        )
        change_rows = [
            ("changed", compact_path(path, 34), "modified")
            for path in self._changed_files[-5:]
        ]
        count = len(self._changed_files)
        self.changes_panel.render(
            change_rows,
            empty="尚无文件变更",
            count=f"{count} file" + ("" if count == 1 else "s"),
        )

    def _reset_runtime_panels(self) -> None:
        self._todo_items.clear()
        self._todo_total = self._todo_completed = 0
        self._subagent_items.clear()
        self._changed_files = ()
        self._render_runtime_panels()

    def _handle_result(self, result: Any) -> None:
        self._changed_files = tuple(result.changed_files)
        self._render_runtime_panels()
        self._append_entry("result", result.text or "任务已完成。")
        summary = (
            f"turns={result.turns} · tool_calls={result.tool_calls} · "
            f"changed={list(result.changed_files)}"
        )
        self._append_entry("success", summary)
        if result.verification:
            self._append_entry("success", result.verification)
        self._set_status("complete", "完成")
        self.run_state_title.setText("Completed")
        self.run_meta.setText(
            f"{len(result.changed_files)} files · {result.tool_calls} tool calls"
        )

    def _handle_failure(self, error: Exception) -> None:
        cancelled = isinstance(error, AgentError) and "cancelled" in str(error)
        self._append_entry(
            "warning" if cancelled else "error",
            f"{type(error).__name__}: {error}",
        )
        state = "warning" if cancelled else "error"
        label = "已停止" if cancelled else "失败"
        self._set_status(state, label)
        self.run_state_title.setText("Stopped" if cancelled else "Failed")
        self.run_meta.setText(str(error))

    def _handle_done(self) -> None:
        self.started_at = None
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def _set_status(self, state: str, text: str) -> None:
        self.status_pill.setText(f"●  {text}")
        self.status_pill.setProperty("state", state)
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)
        colors = {
            "ready": "#5F8A70",
            "complete": "#5F8A70",
            "running": "#607EA6",
            "warning": "#A27945",
            "error": "#AD6568",
        }
        self.run_status_dot.setStyleSheet(f"color: {colors[state]};")

    def _refresh_clock(self) -> None:
        if self.started_at is None:
            self.elapsed.setText("00:00")
            return
        elapsed = int(time.monotonic() - self.started_at)
        self.elapsed.setText(f"{elapsed // 60:02d}:{elapsed % 60:02d}")
        if self.status_pill.property("state") == "running":
            self.status_pill.setText(f"●  运行中 · {elapsed}s")

    def _scroll_to_bottom(self) -> None:
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API
        self.cancel_event.set()
        event.accept()


def launch_gui(
    *,
    initial_workspace: Path,
    initial_model: str,
    base_url: str,
    max_turns: int,
    command_timeout: int,
    enable_thinking: bool,
) -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Bailian Code")
    app.setStyle("Fusion")
    app.setFont(QFont("SF Pro Text", 10))
    app.setStyleSheet(APP_STYLE)
    window = CodingAgentWindow(
        initial_workspace=initial_workspace,
        initial_model=initial_model,
        base_url=base_url,
        max_turns=max_turns,
        command_timeout=command_timeout,
        enable_thinking=enable_thinking,
    )
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()
