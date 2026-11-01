"""“其它选项”对话框（原程序 TzPd 窗体：TabControl -> 常规 -> 输出格式）。

确定后写回 WaterMarkH.xml 的 Setting/General/OutFormat，与原程序完全兼容。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..core.config import Config
from ..core.constants import (BTN_CANCEL, BTN_OK, DLG_OUT_FORMAT, DLG_OPTIONS,
                              DLG_TAB_GENERAL, OPT_OUT_FORMATS)
from .theme import enforce_min_size

MIN_WIDTH = 340
MIN_HEIGHT = 210


class OptionsDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, cfg: Config) -> None:
        super().__init__(master)
        self.cfg = cfg
        self.title(DLG_OPTIONS)
        self.transient(master)
        self.resizable(True, True)
        enforce_min_size(self, MIN_WIDTH, MIN_HEIGHT)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        tab = ttk.Frame(notebook, padding=16)
        notebook.add(tab, text=DLG_TAB_GENERAL)

        ttk.Label(tab, text=DLG_OUT_FORMAT).pack(anchor="w")
        self.var = tk.StringVar(value=OPT_OUT_FORMATS[cfg.out_format])
        self.combo = ttk.Combobox(tab, textvariable=self.var, state="readonly",
                                  values=list(OPT_OUT_FORMATS), width=12)
        self.combo.pack(anchor="w", pady=(4, 12))

        buttons = ttk.Frame(self)
        buttons.pack(fill="x", padx=14, pady=(0, 14))
        ttk.Button(buttons, text=BTN_OK, width=9, command=self._on_ok).pack(side="right")
        ttk.Button(buttons, text=BTN_CANCEL, width=9, command=self.destroy).pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._on_ok())
        self.grab_set()
        self.focus_set()

    def _on_ok(self) -> None:
        self.cfg.out_format = OPT_OUT_FORMATS.index(self.var.get())
        self.cfg.save()
        self.destroy()


def edit(master: tk.Misc, cfg: Config) -> OptionsDialog:
    return OptionsDialog(master, cfg)
