"""主窗口：完整复刻原程序 T9 窗体的两个选项卡、菜单、状态栏与后台线程调度。

布局对照反编译的 InitializeComponent：
  TabControl(Dock=Fill) -> 添加水印 / 提取水印
  每个选项卡 = SplitContainer(247 | 预览)，左侧再分“选项”分组 + “信息”分组 + 按钮行
  MenuStrip -> 工具(其它选项) / 帮助(关于)
  StatusStrip -> 状态标签 + 进度条(100)
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..core.config import Config
from ..core.constants import (APP_TITLE, BTN_ADD, BTN_FONT, BTN_GET,
                              FOLDER_DIALOG_TITLE, FILE_DIALOG_TITLE,
                              FILE_OPEN_PATTERNS, GROUP_INFO, GROUP_OPTIONS,
                              LBL_ADD_CASE, LBL_ADD_IN, LBL_ADD_OUT, LBL_ADD_SCALE,
                              LBL_ADD_TEXT, LBL_GET_CASE, LBL_GET_IN, LBL_GET_SCALE,
                              LBL_PREVIEW, MENU_ABOUT, MENU_HELP, MENU_OPTIONS,
                              MENU_TOOLS, MSG_NO_ADD_IMAGE, MSG_NO_GET_IMAGE,
                              MSG_NO_TEXT, SCHEME_ITEMS, SCHEMES, SPIN_DEFAULT,
                              STATUS_ADD_FAIL, STATUS_ADD_OK, STATUS_GET_FAIL,
                              STATUS_GET_OK, STATUS_READY, TAB_ADD, TAB_GET,
                              TITLE_ERROR, TITLE_HINT, TIP_ADD_SCALE, TIP_ADD_TEXT,
                              TIP_GET_SCALE)
from ..core import pipeline
from ..core.pipeline import AddResult
from ..core.textmask import FontSpec
from ..core.worker import TaskRunner
from . import about_dialog, font_dialog, options_dialog, theme
from .preview import ImagePreview
from .theme import (BUTTON_HEIGHT, BUTTON_WIDTH, INITIAL_HEIGHT, INITIAL_WIDTH,
                    LEFT_PANE_MIN, PALETTE, menu_bar)
from .widgets import ComboField, PathField, SpinField, TextField, ToolTip, WrapLabel, group


class MainWindow:
    """持有 Tk root，构建界面并驱动后台任务。"""

    def __init__(self, root: tk.Tk, cfg: Config | None = None,
                 title: str = f"{APP_TITLE} · Python 复刻") -> None:
        self.root = root
        self.cfg = cfg or Config()
        self.font_spec = FontSpec()
        self.typo = theme.apply(root)
        self.runner = TaskRunner(root)
        self._last_result: AddResult | None = None

        root.title(title)
        root.geometry(f"{INITIAL_WIDTH}x{INITIAL_HEIGHT}")
        root.configure(bg=PALETTE["bg"])
        theme.enforce_min_size(root)

        self._build_menu()
        self._build_status()
        self._build_tabs()
        self._set_busy(False)

        # 内容实测尺寸可能大于原始 MinimumSize（高 DPI / 字体放大时尤其明显），
        # 取两者较大值作为下限，窗口仍可自由缩小，但不会裁掉按钮。
        min_w, min_h = theme.fit_min_size(root)
        root.geometry(f"{max(INITIAL_WIDTH, min_w)}x{max(INITIAL_HEIGHT, min_h)}")
        root.protocol("WM_DELETE_WINDOW", self.close)

    def close(self) -> None:
        """关闭窗口：先停掉轮询，再销毁界面。

        原程序的工作线程是 ``IsBackground = true``，退出时直接结束；
        这里同样让 daemon 线程自生自灭，只要别再把结果回灌给已销毁的窗口。
        """
        self.runner.cancel()
        self.root.destroy()

    # ------------------------------------------------------------------ 菜单
    def _build_menu(self) -> None:
        self.menubar = menu_bar(self.root, self.typo)
        tools = tk.Menu(self.menubar, tearoff=False)
        tools.add_command(label=MENU_OPTIONS, command=self._open_options)
        help_menu = tk.Menu(self.menubar, tearoff=False)
        help_menu.add_command(label=MENU_ABOUT, command=self._open_about)
        self.menubar.add_cascade(label=f"{MENU_TOOLS}(T)", menu=tools)
        self.menubar.add_cascade(label=f"{MENU_HELP}(H)", menu=help_menu)

    def _open_options(self) -> None:
        options_dialog.edit(self.root, self.cfg)

    def _open_about(self) -> None:
        about_dialog.show(self.root, self.typo)

    # ---------------------------------------------------------------- 状态栏
    def _build_status(self) -> None:
        bar = ttk.Frame(self.root, padding=(8, 4))
        bar.pack(side="bottom", fill="x")
        self.status_var = tk.StringVar(value=STATUS_READY)
        self.progress_var = tk.IntVar(value=0)
        ttk.Label(bar, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")
        self.progress = ttk.Progressbar(bar, orient="horizontal", mode="determinate",
                                        maximum=100, variable=self.progress_var, length=170)
        self.progress.pack(side="right")

    # ------------------------------------------------------------------ 选项卡
    def _build_tabs(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(8, 0))

        self.tab_add = ttk.Frame(self.notebook, padding=8)
        self.tab_get = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self.tab_add, text=TAB_ADD)
        self.notebook.add(self.tab_get, text=TAB_GET)
        self._tab_ids = (self.tab_add, self.tab_get)

        self._build_add_tab()
        self._build_get_tab()

        # 原程序 Load 事件里把两个下拉框都设为方案一
        self.add_case.combo.current(0)
        self.get_case.combo.current(0)
        self._show_add_hint(0)
        self._show_get_hint(0)

    def _split(self, parent: ttk.Frame) -> tuple[ttk.Frame, ImagePreview]:
        paned = ttk.Panedwindow(parent, orient="horizontal")
        paned.pack(fill="both", expand=True)
        left = ttk.Frame(paned, width=LEFT_PANE_MIN)
        preview = ImagePreview(paned)
        paned.add(left, weight=0)
        paned.add(preview, weight=1)
        return left, preview

    def _build_add_tab(self) -> None:
        left, self.add_preview_panel = self._split(self.tab_add)

        # 按钮行先以 side=bottom 打包：空间不足时永远是它保留位置，不会被裁掉
        actions = ttk.Frame(left)
        actions.pack(side="bottom", fill="x", pady=(4, 0))
        self.add_button = ttk.Button(actions, text=BTN_ADD, style="Accent.TButton",
                                     command=self._start_add)
        self.add_button.pack()
        self._set_button_extent(self.add_button, BTN_ADD)

        options = group(left, GROUP_OPTIONS)
        options.pack(fill="x", pady=(0, 8))
        self.add_in = PathField(options, LBL_ADD_IN, command=self._pick_add_input)
        self.add_in.pack(fill="x")
        self.add_out = PathField(options, LBL_ADD_OUT, command=self._pick_out_dir)
        self.add_out.pack(fill="x")
        self.add_text_field = TextField(options, LBL_ADD_TEXT, BTN_FONT,
                                        command=self._pick_font, tip=TIP_ADD_TEXT)
        self.add_text_field.pack(fill="x")
        self.add_case = ComboField(options, LBL_ADD_CASE, SCHEME_ITEMS,
                                   on_change=self._show_add_hint)
        self.add_case.pack(fill="x")
        self.add_scale = SpinField(options, LBL_ADD_SCALE, value=SPIN_DEFAULT,
                                   tip=TIP_ADD_SCALE)
        self.add_scale.pack(fill="x")
        self.preview_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options, text=LBL_PREVIEW, variable=self.preview_var).pack(anchor="w")

        info = group(left, GROUP_INFO)
        info.pack(fill="x", pady=(0, 8))
        self.add_info = WrapLabel(info, text=SCHEMES[0].add_text)

    def _build_get_tab(self) -> None:
        left, self.get_preview_panel = self._split(self.tab_get)

        actions = ttk.Frame(left)
        actions.pack(side="bottom", fill="x", pady=(4, 0))
        self.get_button = ttk.Button(actions, text=BTN_GET, style="Accent.TButton",
                                     command=self._start_get)
        self.get_button.pack()
        self._set_button_extent(self.get_button, BTN_GET)

        options = group(left, GROUP_OPTIONS)
        options.pack(fill="x", pady=(0, 8))
        self.get_in = PathField(options, LBL_GET_IN, command=self._pick_get_input)
        self.get_in.pack(fill="x")
        self.get_case = ComboField(options, LBL_GET_CASE, SCHEME_ITEMS,
                                   on_change=self._show_get_hint)
        self.get_case.pack(fill="x")
        self.get_scale = SpinField(options, LBL_GET_SCALE, value=SPIN_DEFAULT,
                                   tip=TIP_GET_SCALE)
        self.get_scale.pack(fill="x")

        info = group(left, GROUP_INFO)
        info.pack(fill="x", pady=(0, 8))
        self.get_info = WrapLabel(info, text=SCHEMES[0].get_text)

    @staticmethod
    def _set_button_extent(button: ttk.Button, label: str) -> None:
        """按钮尺寸贴近原程序 127x36：以字符宽度换算，最小高度用 padding 保证。"""
        button.configure(width=max(14, int(BUTTON_WIDTH / 9)), padding=(10, BUTTON_HEIGHT // 3))
        button.configure(text=label)

    # ---------------------------------------------------------------- 选择文件
    @staticmethod
    def _startup_dir() -> str:
        """文件选择对话框的初始目录：安装态无“程序所在目录”概念，退回用户主目录。"""
        return str(Path.home())

    def _pick_image(self, label: str) -> str:
        return filedialog.askopenfilename(
            title=label, filetypes=list(FILE_OPEN_PATTERNS),
            initialdir=self._startup_dir())

    def _pick_add_input(self) -> None:
        path = self._pick_image(FILE_DIALOG_TITLE)
        if not path:
            return
        self.add_in.set(path)
        if not self.add_out.text:
            self.add_out.set(str(Path(path).parent))   # 原程序同样自动填目录
        self.add_preview_panel.set_image(_load_preview(path))
        self._set_status(STATUS_READY)

    def _pick_get_input(self) -> None:
        path = self._pick_image(FILE_DIALOG_TITLE)
        if not path:
            return
        self.get_in.set(path)
        self.get_preview_panel.set_image(_load_preview(path))
        self._set_status(STATUS_READY)

    def _pick_out_dir(self) -> None:
        initial = self.add_out.text or self._startup_dir()
        path = filedialog.askdirectory(title=FOLDER_DIALOG_TITLE, initialdir=initial)
        if path:
            self.add_out.set(Path(path).as_posix())

    def _pick_font(self) -> None:
        font_dialog.choose(self.root, self.font_spec, preview_text=self.add_text_field.text,
                           on_accept=self._apply_font)

    def _apply_font(self, spec: FontSpec) -> None:
        self.font_spec = spec
        ToolTip(self.add_text_field.entry, lambda: f"{self.font_spec.describe()}（{TIP_ADD_TEXT}）")

    # ------------------------------------------------------------------ 提示
    def _show_add_hint(self, index: int) -> None:
        self.add_info.configure(text=SCHEMES[index].add_text)

    def _show_get_hint(self, index: int) -> None:
        self.get_info.configure(text=SCHEMES[index].get_text)

    # ------------------------------------------------------------------ 校验
    def _validate_add(self) -> bool:
        if not self.add_in.text:
            _hint(self.root, TITLE_HINT, MSG_NO_ADD_IMAGE)
            return False
        if not self.add_text_field.text:
            _hint(self.root, TITLE_HINT, MSG_NO_TEXT)
            return False
        return True

    def _validate_get(self) -> bool:
        if not self.get_in.text:
            _hint(self.root, TITLE_HINT, MSG_NO_GET_IMAGE)
            return False
        return True

    # ------------------------------------------------------------------ 运行
    def _start_add(self) -> None:
        if not self._validate_add() or self.runner.busy:
            return
        source = self.add_in.text
        out_dir = self.add_out.text or str(Path(source).parent)
        scheme = self.add_case.index
        text = self.add_text_field.text
        strength = self.add_scale.value
        brightness = self.get_scale.value
        preview = bool(self.preview_var.get())
        out_format = self.cfg.out_format
        font = self.font_spec

        def work(progress) -> AddResult:
            return pipeline.add_watermark(source, out_dir, text, scheme,
                                          strength_value=strength, font=font,
                                          preview=preview, brightness_value=brightness,
                                          out_format=out_format, progress=progress)

        self._set_busy(True)
        self.runner.submit(work, on_progress=self._set_progress,
                           on_success=self._on_add_done,
                           on_failure=lambda exc: self._on_failure(exc, STATUS_ADD_FAIL))

    def _start_get(self) -> None:
        if not self._validate_get() or self.runner.busy:
            return
        source = self.get_in.text
        scheme = self.get_case.index
        brightness = self.get_scale.value

        def work(progress):
            return pipeline.extract_watermark(source, scheme, brightness, progress=progress)

        self._set_busy(True)
        self.runner.submit(work, on_progress=self._set_progress,
                           on_success=self._on_get_done,
                           on_failure=lambda exc: self._on_failure(exc, STATUS_GET_FAIL))

    def _on_add_done(self, result: AddResult) -> None:
        self._last_result = result
        self._set_busy(False)
        self._set_progress(0, STATUS_ADD_OK)
        shown = result.preview_image if result.preview_image is not None else result.result_image
        self.add_preview_panel.set_image(shown)
        self.status_var.set(f"{STATUS_ADD_OK} -> {result.saved_path}")

    def _on_get_done(self, image) -> None:
        self._set_busy(False)
        self._set_progress(0, STATUS_GET_OK)
        self.get_preview_panel.set_image(image)

    def _on_failure(self, exc: BaseException, fail_text: str) -> None:
        self._set_busy(False)
        self._set_progress(0, fail_text)
        messagebox.showerror(TITLE_ERROR, str(exc) or repr(exc), parent=self.root)

    # ------------------------------------------------------------------ 状态
    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _set_progress(self, percent: int, message: str) -> None:
        self.progress_var.set(max(0, min(100, int(percent))))
        self.status_var.set(message)

    def _set_busy(self, busy: bool) -> None:
        """运行期间禁用两个选项卡，与原程序 m_void_bool 一致。"""
        for index in range(len(self._tab_ids)):
            try:
                self.notebook.tab(index, state="disabled" if busy else "normal")
            except tk.TclError:  # 无显示环境下仅保留按钮状态
                pass
        button_state = "disabled" if busy else "normal"
        self.add_button.configure(state=button_state)
        self.get_button.configure(state=button_state)


def _load_preview(path: str):
    """选图时先显示原图（原程序同样把 Bitmap 放进 PictureBox）。"""
    from ..core import images
    try:
        return images.load_image(path)
    except Exception:
        return None


def _hint(parent: tk.Misc, title: str, message: str) -> None:
    messagebox.showwarning(title, message, parent=parent)


__all__ = ["MainWindow"]
