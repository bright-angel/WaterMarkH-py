"""“关于”对话框（原程序 T10 : Form，标准 WinForms AboutBox）。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..core.constants import (BTN_OK, COMPANY_TEXT, COPYRIGHT_TEXT, DLG_ABOUT,
                              PRODUCT_NAME, VERSION_TEXT)
from .theme import Typography, enforce_min_size

# 原程序 TableLayoutPanel 里的四个 Label（labelProductName / labelVersion /
# labelCopyright / labelCompanyName）在运行时被整体替换成属性值本身，
# 并没有“产品名称：”这样的前缀，标题栏之外也没有额外的产品名标题。
ROWS = (
    PRODUCT_NAME,           # labelProductName  <- AssemblyProduct
    VERSION_TEXT,           # labelVersion      <- "版本 " + Version
    COPYRIGHT_TEXT,         # labelCopyright    <- AssemblyCopyright
    COMPANY_TEXT,           # labelCompanyName  <- AssemblyCompany
)


def show(master: tk.Misc, typo: Typography | None = None) -> tk.Toplevel:
    window = tk.Toplevel(master)
    window.title(f"{DLG_ABOUT} {PRODUCT_NAME}")
    window.resizable(False, False)
    window.transient(master)
    enforce_min_size(window, 360, 220)
    window.configure(bg="#ffffff")

    body = ttk.Frame(window, padding=16)
    body.pack(fill="both", expand=True)
    for index, text in enumerate(ROWS):
        ttk.Label(body, text=text).pack(anchor="w", pady=(index * 2, 0))

    ttk.Button(window, text=BTN_OK, width=10, command=window.destroy).pack(pady=(0, 14))
    window.bind("<Escape>", lambda _e: window.destroy())
    window.grab_set()
    window.focus_set()
    return window
