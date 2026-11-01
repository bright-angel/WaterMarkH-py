"""字体选择对话框（tkinter 没有内置 FontDialog，这里按 WinForms 习惯自建）。

原程序用 ``fontDialog_1``（默认 黑体 9.75 磅）渲染水印文字，
本对话框返回同样的 ``FontSpec``（族名 + 磅值 + 粗体/斜体）。
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import font as tkfont
from tkinter import messagebox, ttk

from ..core.constants import BTN_CANCEL, BTN_OK, DLG_FONT
from ..core.textmask import FontSpec
from .theme import enforce_min_size

MIN_WIDTH = 420
MIN_HEIGHT = 360
SIZE_MIN = 6
SIZE_MAX = 96
PREVIEW_SAMPLE = "隐形水印 WaterMark"


def _families(master: tk.Misc) -> list[str]:
    """系统字体列表，去掉竖向字体（@ 开头）并排序。"""
    try:
        names = [name for name in tkfont.families(master) if not name.startswith("@")]
    except tk.TclError:
        names = []
    return sorted(set(names), key=lambda s: (s.lower(), s))


class FontDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, spec: FontSpec,
                 preview_text: str = "",
                 on_accept: Callable[[FontSpec], None] | None = None) -> None:
        super().__init__(master)
        self.title(DLG_FONT)
        self.transient(master)
        self.resizable(True, True)
        enforce_min_size(self, MIN_WIDTH, MIN_HEIGHT)
        self._on_accept = on_accept

        self.family_var = tk.StringVar(value=spec.family)
        self.point_var = tk.DoubleVar(value=float(spec.point_size))
        self.bold_var = tk.BooleanVar(value=spec.bold)
        self.italic_var = tk.BooleanVar(value=spec.italic)
        self._preview_text = preview_text or PREVIEW_SAMPLE

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        sample = ttk.Frame(body)
        sample.grid(row=0, column=0, columnspan=2, sticky="we")
        ttk.Label(sample, text="预览").pack(anchor="w")
        self.preview_label = ttk.Label(sample, text=self._preview_text, style="Surface.TLabel",
                                       padding=8, relief="solid")
        self.preview_label.pack(fill="x")

        left = ttk.Frame(body)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(left, text="字体").pack(anchor="w")
        list_frame = ttk.Frame(left)
        list_frame.pack(fill="both", expand=True, pady=(2, 0))
        self.listbox = tk.Listbox(list_frame, exportselection=False, activestyle="dotbox",
                                  relief="solid", borderwidth=1)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        right = ttk.Frame(body)
        right.grid(row=1, column=1, sticky="nsew")
        ttk.Label(right, text="样式").pack(anchor="w")
        ttk.Checkbutton(right, text="粗体", variable=self.bold_var,
                        command=self._refresh).pack(anchor="w", pady=(2, 2))
        ttk.Checkbutton(right, text="斜体", variable=self.italic_var,
                        command=self._refresh).pack(anchor="w")
        ttk.Label(right, text="大小（磅）").pack(anchor="w", pady=(10, 0))
        self.size_spin = ttk.Spinbox(right, from_=SIZE_MIN, to=SIZE_MAX, increment=0.25,
                                     textvariable=self.point_var, width=8, justify="right",
                                     command=self._refresh)
        self.size_spin.pack(anchor="w", pady=(2, 0))
        self.size_spin.bind("<KeyRelease>", lambda _e: self._refresh())

        for name in _families(self):
            self.listbox.insert("end", name)
        self._select_initial(spec.family)
        self.listbox.bind("<<ListboxSelect>>", lambda _e: self._refresh())
        self.bold_var.trace_add("write", lambda *_: self._refresh())
        self.italic_var.trace_add("write", lambda *_: self._refresh())

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(buttons, text=BTN_OK, width=9, command=self._accept).pack(side="right")
        ttk.Button(buttons, text=BTN_CANCEL, width=9, command=self.destroy).pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._accept())
        self._refresh()
        self.grab_set()
        self.focus_set()

    # --- 内部 -----------------------------------------------------------
    def _select_initial(self, family: str) -> None:
        index = 0
        for row, name in enumerate(self.listbox.get(0, "end")):
            if name.lower() == family.lower():
                index = row
                break
        self.listbox.selection_set(index)
        self.listbox.see(index)

    def _selected_family(self) -> str:
        chosen = self.listbox.curselection()
        if not chosen:
            return self.family_var.get() or PREVIEW_SAMPLE
        return self.listbox.get(chosen[0])

    def spec(self) -> FontSpec:
        try:
            point = float(self.point_var.get())
        except (TypeError, ValueError):
            point = 9.75
        return FontSpec(family=self._selected_family(),
                        point_size=max(SIZE_MIN, min(SIZE_MAX, point)),
                        bold=bool(self.bold_var.get()),
                        italic=bool(self.italic_var.get()))

    def _refresh(self) -> None:
        spec = self.spec()
        self.family_var.set(spec.family)
        try:
            self.preview_label.configure(font=tkfont.Font(
                master=self, family=spec.family, size=int(round(spec.point_size)),
                weight="bold" if spec.bold else "normal",
                slope="italic" if spec.italic else "roman"))
        except tk.TclError:  # 字体不存在时保持默认字体显示
            pass

    def _accept(self) -> None:
        spec = self.spec()
        try:
            spec.font_file()          # 提前验证 Pillow 能加载该字体
        except FileNotFoundError as exc:
            messagebox.showerror("错误", str(exc), parent=self)
            return
        if self._on_accept is not None:
            self._on_accept(spec)
        self.destroy()


def choose(master: tk.Misc, spec: FontSpec, preview_text: str = "",
           on_accept: Callable[[FontSpec], None] | None = None) -> FontDialog:
    return FontDialog(master, spec, preview_text=preview_text, on_accept=on_accept)
