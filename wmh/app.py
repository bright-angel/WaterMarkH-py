"""应用启动：创建 Tk root、设置图标与 DPI、装配主窗口。

界面装配全部交给 ``wmh.ui.MainWindow``，这里只负责进程级初始化。
"""

from __future__ import annotations

import ctypes
import tkinter as tk
from importlib.resources import files

from .core.config import Config
from .ui.main_window import MainWindow

# 图标随包一起分发，无论开发态还是安装态都能用 importlib.resources 取到
ASSET_ICON = files("wmh").joinpath("assets", "app.ico")


def _enable_high_dpi() -> None:
    """Windows 下开启每显示器 DPI 感知，避免高分屏文字发虚。"""
    if not hasattr(ctypes, "windll"):
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _apply_icon(root: tk.Tk) -> None:
    try:
        icon_path = ASSET_ICON
        if icon_path.is_file():
            root.iconbitmap(str(icon_path))
    except (tk.TclError, TypeError):
        pass


def build_root(cfg: Config | None = None) -> tuple[tk.Tk, MainWindow]:
    _enable_high_dpi()
    root = tk.Tk(className="WaterMarkH")
    window = MainWindow(root, cfg=cfg)
    _apply_icon(root)
    return root, window


def run(cfg: Config | None = None) -> int:
    root, _window = build_root(cfg)
    root.mainloop()
    return 0
