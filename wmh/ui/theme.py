"""集中管理界面样式与尺寸约束。

所有颜色、字体、间距、最小窗口尺寸都在这里定义，界面模块只引用不硬编码，
改主题只需动这一个文件（对应“代码要集中管理”的要求）。
"""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

# --- 窗口尺寸约束（原程序 ClientSize 764x511 / MinimumSize 780x550）---------
MIN_WIDTH = 780
MIN_HEIGHT = 550
INITIAL_WIDTH = 980
INITIAL_HEIGHT = 620

# --- 版面尺寸 --------------------------------------------------------------
LEFT_PANE_WIDTH = 268
LEFT_PANE_MIN = 236
PREVIEW_MIN_WIDTH = 300
CONTROL_WIDTH = 176          # 原程序输入框宽度 169~168
BUTTON_WIDTH = 126           # 原程序“添加水印/提取水印”按钮 127x36
BUTTON_HEIGHT = 34
INFO_WRAP = 240              # “信息”分组长文本换行宽度
TOOLTIP_WRAP = 300

PALETTE = {
    "bg": "#f2f3f5",
    "surface": "#ffffff",
    "canvas": "#202124",
    "text": "#1f2328",
    "muted": "#57606a",
    "accent": "#2f6feb",
    "border": "#d0d7de",
    "menu": "#ffffff",
    "menu_active": "#deebff",
}

FONT_CANDIDATES = ("Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", "Tahoma", "宋体")


@dataclass(frozen=True)
class Typography:
    family: str
    size: int = 10
    heading_size: int = 11

    @property
    def scale(self) -> float:
        return self.size / 10.0


def pick_font_family(root: tk.Misc) -> str:
    """在系统可用字体里挑一个界面字体，保证中文不会变成方框。"""
    try:
        from tkinter import font as tkfont
        available = {name.lower(): name for name in tkfont.families(root)}
    except Exception:  # 无显示环境下的兜底
        return "TkDefaultFont"
    for candidate in FONT_CANDIDATES:
        hit = available.get(candidate.lower())
        if hit:
            return hit
    return "TkDefaultFont"


def apply(root: tk.Misc) -> Typography:
    """配置 ttk 样式并返回字号信息，供对话框复用。"""
    family = pick_font_family(root)
    typo = Typography(family=family)

    root.option_add("*Font", (family, typo.size))
    root.configure(bg=PALETTE["bg"])

    style = ttk.Style(root)
    for preferred in ("vista", "clam", "default"):
        if preferred in style.theme_names():
            style.theme_use(preferred)
            break

    style.configure(".", background=PALETTE["bg"], foreground=PALETTE["text"],
                    font=(family, typo.size), bordercolor=PALETTE["border"],
                    lightcolor=PALETTE["bg"], darkcolor=PALETTE["bg"])
    style.configure("TFrame", background=PALETTE["bg"])
    style.configure("Card.TFrame", background=PALETTE["surface"])
    style.configure("TLabel", background=PALETTE["bg"], foreground=PALETTE["text"])
    style.configure("Surface.TLabel", background=PALETTE["surface"], foreground=PALETTE["text"])
    style.configure("Muted.TLabel", background=PALETTE["bg"], foreground=PALETTE["muted"])
    style.configure("Heading.TLabel", background=PALETTE["bg"], foreground=PALETTE["text"],
                    font=(family, typo.heading_size, "bold"))
    style.configure("TLabelframe", background=PALETTE["bg"], bordercolor=PALETTE["border"])
    style.configure("TLabelframe.Label", background=PALETTE["bg"], foreground=PALETTE["muted"],
                    font=(family, typo.size, "bold"))
    style.configure("TButton", padding=(10, 5), background=PALETTE["surface"],
                    foreground=PALETTE["text"], bordercolor=PALETTE["border"])
    style.map("TButton", background=[("active", PALETTE["menu_active"])])
    style.configure("Accent.TButton", padding=(10, 8), font=(family, typo.size, "bold"))
    style.configure("TNotebook", background=PALETTE["bg"], bordercolor=PALETTE["border"], tabmargins=(8, 6, 8, 2))
    style.configure("TNotebook.Tab", padding=(16, 6), background=PALETTE["bg"])
    style.map("TNotebook.Tab", background=[("selected", PALETTE["surface"])],
              foreground=[("selected", PALETTE["accent"])])
    style.configure("TCombobox", fieldbackground=PALETTE["surface"], background=PALETTE["surface"],
                    arrowcolor=PALETTE["text"], padding=3)
    style.configure("TEntry", fieldbackground=PALETTE["surface"], insertcolor=PALETTE["text"])
    style.configure("TSpinbox", fieldbackground=PALETTE["surface"], arrowcolor=PALETTE["text"])
    style.configure("TCheckbutton", background=PALETTE["bg"])
    style.configure("TProgressbar", background=PALETTE["accent"], troughcolor=PALETTE["surface"],
                    bordercolor=PALETTE["border"], lightcolor=PALETTE["accent"],
                    darkcolor=PALETTE["accent"], thickness=14)
    style.configure("Horizontal.TPanedWindow", background=PALETTE["border"], sashwidth=6)
    style.configure("TSizegrip", background=PALETTE["bg"])

    root.option_add("*TCombobox*Listbox*Background", PALETTE["surface"])
    root.option_add("*TCombobox*Listbox*SelectBackground", PALETTE["menu_active"])
    return typo


def menu_bar(root: tk.Misc, typo: Typography) -> tk.Menu:
    """创建与主题一致的菜单栏（tk.Menu 不走 ttk 样式）。"""
    menubar = tk.Menu(root, tearoff=False, bg=PALETTE["menu"], fg=PALETTE["text"],
                      activebackground=PALETTE["menu_active"], activeforeground=PALETTE["accent"],
                      borderwidth=1, font=(typo.family, typo.size))
    root.config(menu=menubar)
    return menubar


def enforce_min_size(window: tk.Misc, width: int = MIN_WIDTH, height: int = MIN_HEIGHT) -> None:
    """窗口可以任意缩放，但不得小于原始 MinimumSize。"""
    if isinstance(window, tk.Tk):
        window.minsize(width, height)
        return

    def on_configure(event) -> None:
        if event.width < width or event.height < height:
            window.geometry(f"{max(event.width, width)}x{max(event.height, height)}")

    window.bind("<Configure>", on_configure, add="+")


def fit_min_size(window: tk.Misc, width: int = MIN_WIDTH, height: int = MIN_HEIGHT) -> tuple[int, int]:
    """把最小尺寸抬到“内容真正需要的大小”。

    原程序的 MinimumSize 是 780x550，但那是 96 DPI、WinForms 绝对布局下的数值；
    换成 ttk 自适应布局 + 高 DPI 缩放后，同样的数值会把最下面的按钮裁掉。
    这里以原始值为下限，再按实测的 reqwidth/reqheight 取较大者，
    保证窗口缩到最小时所有控件仍然完整可见。
    """
    window.update_idletasks()
    minimum = (max(width, int(window.winfo_reqwidth())),
               max(height, int(window.winfo_reqheight())))
    window.minsize(*minimum)
    return minimum


def wraplength_for(widget: tk.Misc, minimum: int = INFO_WRAP, fraction: float = 0.85) -> int:
    """长提示换行宽度：跟随父容器，但不小于 minimum。"""
    try:
        width = widget.winfo_width()
    except tk.TclError:
        return minimum
    if width <= 1:
        return minimum
    return max(minimum, int(width * fraction))
