"""图片预览面板：等比例缩放显示（对应 PictureBox.SizeMode = Zoom）。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from .theme import PALETTE, PREVIEW_MIN_WIDTH

BACKGROUND = PALETTE["canvas"]


class ImagePreview(ttk.Frame):
    """带深色底、保持宽高比的图片显示区域。"""

    def __init__(self, master: tk.Misc, min_width: int = PREVIEW_MIN_WIDTH,
                 min_height: int = 220) -> None:
        super().__init__(master)
        self.canvas = tk.Canvas(self, background=BACKGROUND, highlightthickness=0,
                                width=min_width, height=min_height, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._redraw())
        self._image: Image.Image | None = None
        self._photo: ImageTk.PhotoImage | None = None

    # --- 对外接口 -------------------------------------------------------
    def set_image(self, image: Image.Image | None) -> None:
        self._image = image
        self._redraw()

    def clear(self) -> None:
        self.set_image(None)

    # --- 内部实现 -------------------------------------------------------
    def _redraw(self) -> None:
        self.canvas.delete("all")
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        if self._image is None:
            self.canvas.create_text(width // 2, height // 2, text="暂无图片",
                                    fill="#8b949e", anchor="center")
            return
        scale = min(width / self._image.width, height / self._image.height)
        size = (max(1, int(self._image.width * scale)), max(1, int(self._image.height * scale)))
        rendered = self._image.convert("RGB").resize(size, Image.BILINEAR)
        self._photo = ImageTk.PhotoImage(rendered)
        self.canvas.create_image(width // 2, height // 2, image=self._photo, anchor="center")
