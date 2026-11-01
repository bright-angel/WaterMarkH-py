"""水印文字位图：黑底白字，居中，最后整体旋转 180°。

对应反编译的 m_bmp_string_int_int(string 文字, int 宽, int 高)：
  FillRectangle(Brushes.Black) -> DrawString(Brushes.White, w/2 - tw/2, h/2 - th)
  -> 把 BGRA 像素序列整体逆序写回（等价于旋转 180°）。

旋转是有意的：提取出来的是幅度谱，图像上下颠倒不影响水印文字被再次翻转回正。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import fonts as font_lib
from .constants import DEFAULT_FONT_FAMILY, DEFAULT_FONT_POINT


@dataclass(frozen=True)
class FontSpec:
    """界面与算法之间传递的字体描述（磅值，与 WinForms FontDialog 一致）。"""

    family: str = DEFAULT_FONT_FAMILY
    point_size: float = DEFAULT_FONT_POINT
    bold: bool = False
    italic: bool = False

    @property
    def pixel_size(self) -> int:
        return font_lib.point_to_pixels(self.point_size)

    def with_point_size(self, point_size: float) -> FontSpec:
        return replace(self, point_size=point_size)

    def font_file(self) -> Path:
        return font_lib.resolve_path(self.family)

    def load(self) -> ImageFont.FreeTypeFont:
        """Pillow 10.x 没有 font_variant，粗体用描边、斜体用错切近似。"""
        return ImageFont.truetype(str(self.font_file()), size=self.pixel_size, index=0)

    def describe(self) -> str:
        styles = []
        if self.bold:
            styles.append("粗体")
        if self.italic:
            styles.append("斜体")
        style = " ".join(styles) if styles else "常规"
        return f"{self.family} {style} {self.point_size:g} 磅"


def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[float, float]:
    """近似 GDI+ 的 MeasureString：返回 (宽, 高)，高为字体行高。"""
    width = draw.textlength(text, font=font)
    ascent, descent = font.getmetrics()
    return float(width), float(ascent + descent)


def _shear(layer: Image.Image, factor: float = -0.25) -> Image.Image:
    """斜体近似：按行水平错切（保持画布尺寸不变）。"""
    width, height = layer.size
    return layer.transform(layer.size, Image.Transform.AFFINE,
                          (1, factor, -factor * height / 2.0, 0, 1, 0),
                          resample=Image.BILINEAR)


def build_mask(text: str, size: tuple[int, int], spec: FontSpec | None = None) -> Image.Image:
    """生成与画布同尺寸的水印掩膜（RGB，黑底白字，已旋转 180°）。"""
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError("水印图尺寸必须为正数")
    spec = spec or FontSpec()
    mask = Image.new("RGB", (width, height), (0, 0, 0))
    if not text:
        return mask

    font = spec.load()
    layer = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(layer)
    text_width, text_height = _measure(draw, text, font)
    x = width / 2.0 - text_width / 2.0
    y = height / 2.0 - text_height
    draw.text((x, y), text, font=font, fill=255,
              stroke_width=1 if spec.bold else 0, stroke_fill=255)
    if spec.italic:
        layer = _shear(layer)
    mask.paste((255, 255, 255), (0, 0), layer)
    return mask.rotate(180)
