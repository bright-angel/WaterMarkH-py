"""可复用的 tkinter 小控件：分组、带按钮的路径输入、数字输入、换行标签、悬停提示。

主窗口 / 对话框都从这里取控件，避免在每个界面里重复搭建布局。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from ..core.constants import SPIN_DEFAULT, SPIN_MAX, SPIN_MIN
from .theme import INFO_WRAP, PALETTE, TOOLTIP_WRAP


def group(parent: ttk.Frame, title: str, padding: int = 10) -> ttk.Labelframe:
    frame = ttk.Labelframe(parent, text=title, padding=padding)
    return frame


def stack(parent: ttk.Frame) -> ttk.Frame:
    """纵向堆叠容器（每行占满宽度，控件之间留一致间距）。"""
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=(0, 8))
    return frame


class WrapLabel(ttk.Label):
    """长提示自动换行的标签，宽度跟随父容器且不小于 min_width。"""

    def __init__(self, master: ttk.Frame, text: str = "", min_width: int = INFO_WRAP,
                 style: str = "Muted.TLabel", **kwargs) -> None:
        super().__init__(master, text=text, style=style, justify="left",
                         wraplength=min_width, **kwargs)
        self._min_width = min_width
        self.pack(fill="x", expand=False)
        self.bind("<Configure>", self._reflow, add="+")

    def _reflow(self, event: tk.Event) -> None:
        target = max(self._min_width, int(event.width * 0.94))
        if int(self.cget("wraplength")) != target:
            self.configure(wraplength=target)


class PathField(ttk.Frame):
    """“标签 + 文本框 + 浏览按钮”三件套，对应原程序的 textBox + button。"""

    def __init__(self, master: ttk.Frame, label: str, command: Callable[[], None] | None = None,
                 browse_text: str = "浏览", tip: str | None = None) -> None:
        super().__init__(master)
        self.var = tk.StringVar()
        ttk.Label(self, text=label).pack(anchor="w")
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(2, 6))
        self.button = ttk.Button(row, text=browse_text, width=5, command=self._on_browse)
        self.button.pack(side="right")
        self.entry = ttk.Entry(row, textvariable=self.var, width=1)
        self.entry.pack(side="left", fill="x", expand=True)
        self._command = command
        if tip:
            ToolTip(self.entry, tip)

    def _on_browse(self) -> None:
        if self._command is not None:
            self._command()

    @property
    def text(self) -> str:
        return self.var.get().strip()

    def set(self, value: str) -> None:
        self.var.set(value)

    def set_command(self, command: Callable[[], None]) -> None:
        self._command = command


class TextField(PathField):
    """“标签 + 文本框 + 字体按钮”，用于水印文字输入。"""

    def __init__(self, master: ttk.Frame, label: str, action_text: str,
                 command: Callable[[], None] | None = None, tip: str | None = None) -> None:
        super().__init__(master, label, command=command, browse_text=action_text, tip=tip)


class SpinField(ttk.Frame):
    """数字输入（原程序 NumericUpDown：0~1000，默认 50）。"""

    def __init__(self, master: ttk.Frame, label: str, value: int = SPIN_DEFAULT,
                 from_: int = SPIN_MIN, to: int = SPIN_MAX, tip: str | None = None) -> None:
        super().__init__(master)
        self.var = tk.IntVar(value=value)
        ttk.Label(self, text=label).pack(anchor="w")
        self.spin = ttk.Spinbox(self, from_=from_, to=to, textvariable=self.var,
                                width=12, justify="right")
        self.spin.pack(anchor="w", pady=(2, 6), fill="x")
        if tip:
            ToolTip(self.spin, tip)

    @property
    def value(self) -> int:
        try:
            return int(self.spin.get())
        except (TypeError, ValueError):
            return SPIN_DEFAULT


class ComboField(ttk.Frame):
    """下拉选择（原程序 ComboBox，宽度与输入框一致）。"""

    def __init__(self, master: ttk.Frame, label: str, values: tuple[str, ...],
                 on_change: Callable[[int], None] | None = None) -> None:
        super().__init__(master)
        self.var = tk.StringVar(value=values[0])
        self._on_change = on_change
        ttk.Label(self, text=label).pack(anchor="w")
        self.combo = ttk.Combobox(self, textvariable=self.var, values=list(values),
                                  state="readonly")
        self.combo.pack(anchor="w", pady=(2, 6), fill="x")
        self.combo.bind("<<ComboboxSelected>>", self._notify, add="+")

    def _notify(self, _event=None) -> None:
        if self._on_change is not None:
            self._on_change(self.index)

    @property
    def index(self) -> int:
        return self.combo.current()


class ToolTip:
    """鼠标悬停提示（原程序 toolTip.SetToolTip）。"""

    def __init__(self, widget: tk.Misc, text: str | Callable[[], str],
                 wraplength: int = TOOLTIP_WRAP) -> None:
        self.widget = widget
        self._text = text
        self.wraplength = wraplength
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _resolve(self) -> str:
        return self._text() if callable(self._text) else self._text

    def _show(self, _event=None) -> None:
        text = self._resolve()
        if not text or self._window is not None:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._window = window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        tk.Label(window, text=text, justify="left", wraplength=self.wraplength,
                 background="#fffbe6", foreground=PALETTE["text"],
                 relief="solid", borderwidth=1, padx=8, pady=6).pack()

    def _hide(self, _event=None) -> None:
        if self._window is not None:
            self._window.destroy()
            self._window = None
