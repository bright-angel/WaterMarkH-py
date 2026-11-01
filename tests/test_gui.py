"""界面自测：主窗口装配、最小尺寸约束、长文本换行、对话框，以及走完整流程。

需要可用显示环境（Windows 桌面）。没有 Tk 时整个模块跳过。
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wmh.core import formats                        # noqa: E402
from wmh.core.config import Config                  # noqa: E402
from wmh.core.constants import (GROUP_INFO, MSG_NO_ADD_IMAGE, MSG_NO_GET_IMAGE,  # noqa: E402
                                MSG_NO_TEXT, SCHEMES, SPIN_DEFAULT, STATUS_ADD_OK,
                                STATUS_GET_OK, TAB_ADD, TAB_GET)

try:
    import tkinter as tk
    from tkinter import ttk
    tk.Tk().destroy()
except Exception:  # pragma: no cover - 无显示环境
    tk = None
    ttk = None

from .test_core import make_photo  # noqa: E402

SKIP_REASON = "当前环境无法创建 Tk 窗口，跳过界面测试"


def _spin(root: tk.Tk, runner, timeout: float = 60.0) -> None:
    """像 mainloop 那样驱动事件，直到后台任务结束且结果都已回灌。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        root.update()
        if runner.is_idle():
            root.update()
            return
        time.sleep(0.01)
    raise TimeoutError("界面后台任务超时")


def _open_window(tmp: Path):
    from wmh.ui import main_window as mw
    from wmh.ui.main_window import MainWindow

    # 弹窗在自动化测试里会阻塞整个进程：换成快速失败的异常，让断言直接给出原因
    class FailFast:
        @staticmethod
        def _raise(title, message, **_kw):
            raise AssertionError(f"界面弹窗 [{title}] {message}")

        showwarning = showerror = showinfo = _raise

    mw.messagebox = FailFast

    root = tk.Tk()
    root.withdraw()
    window = MainWindow(root, cfg=Config(tmp / "WaterMarkH.xml"))
    root.deiconify()
    root.update_idletasks()
    root.update()
    return root, window


def test_main_window_layout() -> None:
    if tk is None:  # pragma: no cover
        print(f"跳过：{SKIP_REASON}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        root, window = _open_window(Path(tmp))
        try:
            assert root.title().startswith("隐形水印工具 V1.2"), root.title()
            min_w, min_h = root.minsize()
            assert min_w >= 780 and min_h >= 550, f"最小尺寸被改小：{min_w}x{min_h}"
            assert root.winfo_width() >= min_w, "窗口宽度不得小于最小宽度"
            assert window.notebook.tabs().__len__() == 2
            texts = [window.notebook.tab(tab, "text") for tab in window.notebook.tabs()]
            assert texts == [TAB_ADD, TAB_GET], texts
            # 控件齐全
            for field in (window.add_in, window.add_out, window.add_text_field,
                          window.add_case, window.add_scale, window.get_in,
                          window.get_case, window.get_scale):
                assert field.winfo_exists(), field
            assert tuple(window.add_case.combo["values"]) == tuple(s.name for s in SCHEMES)
            assert tuple(window.get_case.combo["values"]) == tuple(s.name for s in SCHEMES)
            assert window.add_scale.value == SPIN_DEFAULT
            assert window.get_scale.value == SPIN_DEFAULT
            assert window.add_info.cget("text") == SCHEMES[0].add_text
            assert window.get_info.cget("text") == SCHEMES[0].get_text
            assert int(window.add_info.cget("wraplength")) >= 200, "长提示必须换行"
            labels = [window.menubar.entrycget(index, "label")
                      for index in range(window.menubar.index("end") + 1)]
            assert "工具(T)" in labels and "帮助(H)" in labels, labels
            _assert_no_clipping(window)
        finally:
            window.close()


def _assert_no_clipping(window) -> None:
    """缩到最小尺寸时，两个选项卡里的按钮都必须完整可见（不得被面板裁掉）。"""
    root = window.root
    min_w, min_h = root.minsize()
    root.geometry(f"{min_w}x{min_h}")
    root.update_idletasks()
    root.update()
    for tab, button in ((window.tab_add, window.add_button),
                        (window.tab_get, window.get_button)):
        window.notebook.select(tab)      # 只有当前选项卡的子控件才会被 map
        root.update_idletasks()
        root.update()
        assert button.winfo_ismapped(), f"{button} 未显示"
        assert button.winfo_height() >= button.winfo_reqheight(), "按钮高度被压缩"
        tab_bottom = tab.winfo_rooty() + tab.winfo_height()
        button_bottom = button.winfo_rooty() + button.winfo_height()
        assert button_bottom <= tab_bottom + 1, (
            f"按钮底部 {button_bottom} 超出选项卡 {tab_bottom}，最小尺寸下被裁切")
    window.notebook.select(window.tab_add)


def test_scheme_hint_updates() -> None:
    if tk is None:  # pragma: no cover
        return
    with tempfile.TemporaryDirectory() as tmp:
        root, window = _open_window(Path(tmp))
        try:
            for index, info in enumerate(SCHEMES):
                window._show_add_hint(index)
                window._show_get_hint(index)
                root.update_idletasks()
                assert window.add_info.cget("text") == info.add_text
                assert window.get_info.cget("text") == info.get_text
                assert info.name in window.add_info.cget("text")
            assert int(window.add_info.cget("wraplength")) >= 200
        finally:
            window.close()


def test_validation_messages_match_original() -> None:
    assert MSG_NO_ADD_IMAGE == "请选择需要添加水印的图片文件。"
    assert MSG_NO_TEXT == "请输入水印文字。"
    assert MSG_NO_GET_IMAGE == "请选择需要提取水印的图片文件。"
    assert GROUP_INFO == "信息"


def _state(widget) -> str:
    """ttk 控件的 ``widget["state"]`` 返回 Tcl index 对象，这里统一取字符串。"""
    return " ".join(str(value) for value in widget.state()) if hasattr(widget, "state") else ""


def _disabled(widget) -> bool:
    """运行期间控件应处于 disabled 状态（ttk 用 instate 判断，不能比较 cget）。"""
    return widget.instate(["disabled"])


def test_add_and_extract_through_ui() -> None:
    if tk is None:  # pragma: no cover
        return
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        source = folder / "photo.png"
        make_photo(300, 200).save(source)
        root, window = _open_window(folder)
        try:
            window.add_in.set(str(source))
            window.add_out.set(str(folder))
            window.add_text_field.set("隐形水印测试")
            window.add_case.combo.current(1)
            window._start_add()
            assert _disabled(window.add_button), "运行期间按钮应禁用"
            assert _disabled(window.get_button), "运行期间另一个选项卡的按钮也应禁用"
            _spin(root, window.runner)
            assert (folder / "photo_WaterMark.jpg").is_file()
            assert STATUS_ADD_OK in window.status_var.get()
            assert window.add_preview_panel._image is not None
            assert not _disabled(window.add_button), _state(window.add_button)
            assert not _disabled(window.get_button)

            saved = folder / "photo_WaterMark.jpg"
            window.get_in.set(str(saved))
            window.get_case.combo.current(1)
            window._start_get()
            _spin(root, window.runner)
            assert STATUS_GET_OK in window.status_var.get()
            assert window.get_preview_panel._image.size == (300, 200)
        finally:
            window.close()


def test_options_dialog_persists_format() -> None:
    if tk is None:  # pragma: no cover
        return
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Config(Path(tmp) / "WaterMarkH.xml")
        root = tk.Tk()
        root.withdraw()
        try:
            from wmh.ui.options_dialog import OptionsDialog

            dialog = OptionsDialog(root, cfg)
            root.update()
            dialog.combo.current(formats.PNG)
            dialog.var.set("PNG")
            dialog._on_ok()
            root.update()
            assert Config(cfg.path).out_format == formats.PNG
        finally:
            root.destroy()


def test_font_dialog_and_about_dialog() -> None:
    if tk is None:  # pragma: no cover
        return
    from wmh.core.textmask import FontSpec

    with tempfile.TemporaryDirectory():
        root = tk.Tk()
        root.withdraw()
        try:
            from wmh.ui.about_dialog import show as show_about
            from wmh.ui.font_dialog import FontDialog

            about = show_about(root)
            root.update()
            assert about.winfo_exists()
            about.event_generate("<Escape>")
            about.destroy()

            picked: list[FontSpec] = []
            dialog = FontDialog(root, FontSpec(), preview_text="测试", on_accept=picked.append)
            root.update()
            assert dialog.listbox.size() > 0, "字体列表不应为空"
            dialog.listbox.selection_clear(0, "end")
            dialog.listbox.selection_set(0)
            dialog.point_var.set(18.0)
            dialog.bold_var.set(True)
            dialog._accept()
            root.update()
            assert picked and picked[0].point_size == 18.0 and picked[0].bold
        finally:
            root.destroy()
