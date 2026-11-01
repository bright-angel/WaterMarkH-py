"""端到端业务流程：添加水印、提取水印，并复刻原程序的进度百分比节奏。

对应反编译的 m_void_void#5（添加线程体）与 m_void_void#6（提取线程体）。
这里的 ``progress(percent, message)`` 就是原程序的 ``m_void_int_string``，
由 UI 层的后台线程回调到主线程刷新状态栏与进度条。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from . import config as config_mod
from . import formats, images, schemes, textmask, watermark
from .constants import (BRIGHTNESS_DIVISOR, STATUS_ADD_OK, STATUS_BUSY_ADD,
                        STATUS_BUSY_GET, STATUS_PREVIEW, SPIN_DEFAULT,
                        STRENGTH_DIVISOR)

Progress = Callable[[int, str], None]


@dataclass(frozen=True)
class AddResult:
    saved_path: Path
    result_image: Image.Image
    preview_image: Image.Image | None
    status: str = STATUS_ADD_OK


def _mapper(base: int, span: int, label: str, progress: Progress | None) -> watermark.Progress:
    """把算法内部的相对进度(0/10/…/90)映射成原程序的状态栏数值。"""

    def report(relative: int) -> None:
        if progress is None:
            return
        value = base + span * relative // 100
        message = label if relative == 0 else f"{label} {value}%"
        progress(value, message)

    return report


def strength_of(spin_value: float) -> float:
    """水印强度：原程序 (int)numericUpDown_1.Value / 500f。"""
    return float(spin_value) / STRENGTH_DIVISOR


def gain_of(spin_value: float) -> float:
    """图像亮度：原程序 (int)numericUpDown_2.Value / 5f。"""
    return float(spin_value) / BRIGHTNESS_DIVISOR


def add_watermark(source: str | Path,
                  out_dir: str | Path,
                  text: str,
                  scheme: int,
                  strength_value: int = SPIN_DEFAULT,
                  font: textmask.FontSpec | None = None,
                  preview: bool = False,
                  brightness_value: int = SPIN_DEFAULT,
                  out_format: int | None = None,
                  cfg: config_mod.Config | None = None,
                  progress: Progress | None = None) -> AddResult:
    """添加水印 -> 保存 -> 可选生成“提取预览”。

    预览走的是提取算法，因此沿用“提取水印”页的图像亮度设置，与原程序一致
    （原程序的提取核心始终读取 numericUpDown_2.Value）。
    """
    if out_format is None:
        out_format = (cfg or config_mod.Config()).out_format

    image = images.load_image(source)
    canvas = schemes.prepare_embed(image, scheme)
    mask = textmask.build_mask(text, canvas.image.size, font)

    span = 50 if preview else 100
    data = watermark.embed(images.to_array(canvas.image), images.to_array(mask),
                           strength_of(strength_value),
                           _mapper(0, span, STATUS_BUSY_ADD, progress))
    result = canvas.restore(images.from_array(data))

    saved = formats.save(result, formats.output_path(source, out_dir, out_format), out_format)

    preview_image: Image.Image | None = None
    if preview:
        preview_image = extract_watermark(result, scheme, brightness_value,
                                          base=50, span=50, label=STATUS_PREVIEW,
                                          progress=progress)
    if progress is not None:
        progress(0, STATUS_ADD_OK)
    return AddResult(saved, result, preview_image)


def extract_watermark(source: str | Path | Image.Image,
                      scheme: int,
                      brightness_value: int = SPIN_DEFAULT,
                      base: int = 0,
                      span: int = 100,
                      label: str = STATUS_BUSY_GET,
                      progress: Progress | None = None) -> Image.Image:
    """提取水印：返回幅度谱图像（水印文字可见），原程序只在界面显示、不落盘。"""
    image = source if isinstance(source, Image.Image) else images.load_image(source)
    canvas = schemes.prepare_extract(image, scheme)
    data = watermark.extract(images.to_array(canvas.image), gain_of(brightness_value),
                             _mapper(base, span, label, progress))
    return canvas.restore(images.from_array(data))
