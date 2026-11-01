"""五种“转换方案”：把任意尺寸的图片送到 2 的整数次幂画布上，水印后再还原。

对应反编译的 m_bmp_bmp_int_string_int_int（添加）与同名 #2（提取）。
两个函数的分支必须与转换方案编号一一对应，否则提取时选错方案就取不出水印。

  方案一  round 到 2 的幂，直接输出该尺寸（比例可能变化）
  方案二  round 到 2 的幂做双线性缩放，再双线性缩放回原尺寸
  方案三  round 到 2 的幂做最近邻缩放，再最近邻缩放回原尺寸（适用小图）
  方案四  ceil 到 2 的幂，白底（提取时黑底）填充后 1:1 贴入，再裁回原尺寸
  方案五  floor 到 2 的幂，取原图左上角 1:1 区域，水印后贴回原图（只覆盖局部）
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from PIL import Image

from .constants import SCHEME_ITEMS, SCHEMES, SchemeInfo
from .images import KIND_HIGH, KIND_NEAREST, resize

ROUND = "round"
CEIL = "ceil"
FLOOR = "floor"

ResizeFn = Callable[[Image.Image], Image.Image]


def power_of_two(value: int, mode: str = ROUND) -> int:
    """复刻 (int)Math.Pow(2, Math.{Round,Ceiling,Floor}(Math.Log(w, 2)))。"""
    if value < 1:
        raise ValueError("图像尺寸必须大于 0")
    exponent = math.log2(value)
    exponent = {"round": round(exponent), "ceil": math.ceil(exponent),
                "floor": math.floor(exponent)}[mode]
    return 1 << int(exponent)


@dataclass
class Canvas:
    """画布图像 + 处理完之后的还原动作。"""

    image: Image.Image
    finish: ResizeFn
    scheme: int

    def restore(self, processed: Image.Image) -> Image.Image:
        return self.finish(processed)


def _identity(im: Image.Image) -> Image.Image:
    return im


def _paste_back(original: Image.Image) -> ResizeFn:
    """方案五：把水印花布 1:1 贴回原图左上角，其余区域保持原样。"""

    def finish(processed: Image.Image) -> Image.Image:
        out = original.copy()
        out.paste(processed, (0, 0))
        return out

    return finish


def _crop_to(original: Image.Image) -> ResizeFn:
    w, h = original.size

    def finish(processed: Image.Image) -> Image.Image:
        return processed.crop((0, 0, w, h))

    return finish


def _resize_to(original: Image.Image, kind: int = KIND_HIGH) -> ResizeFn:
    size = original.size

    def finish(processed: Image.Image) -> Image.Image:
        return resize(processed, size, kind)

    return finish


def _crop_to_canvas(original: Image.Image, size: tuple[int, int]) -> Image.Image:
    """new Bitmap(w,h) + DrawImage(src, rect(0,0,w,h), rect(0,0,w,h))：黑底 + 左上 1:1 区域。"""
    canvas = Image.new("RGB", size, (0, 0, 0))
    canvas.paste(original.crop((0, 0, size[0], size[1])), (0, 0))
    return canvas


def _pad_canvas(original: Image.Image, size: tuple[int, int], fill: tuple[int, int, int]) -> Image.Image:
    canvas = Image.new("RGB", size, fill)
    canvas.paste(original, (0, 0))
    return canvas


def _round_size(im: Image.Image, mode: str = ROUND) -> tuple[int, int]:
    return power_of_two(im.width, mode), power_of_two(im.height, mode)


def prepare_embed(im: Image.Image, scheme: int) -> Canvas:
    if scheme in (0, 1, 2):
        size = _round_size(im)
        kind = KIND_NEAREST if scheme == 2 else KIND_HIGH
        canvas = resize(im, size, kind)
        finish = _identity if scheme == 0 else _resize_to(im, kind)
        return Canvas(canvas, finish, scheme)
    if scheme == 3:
        size = _round_size(im, CEIL)
        return Canvas(_pad_canvas(im, size, (255, 255, 255)), _crop_to(im), scheme)
    if scheme == 4:
        size = _round_size(im, FLOOR)
        return Canvas(_crop_to_canvas(im, size), _paste_back(im), scheme)
    raise ValueError(f"未知的转换方案编号：{scheme}")


def prepare_extract(im: Image.Image, scheme: int) -> Canvas:
    if scheme in (0, 1, 2):
        # 原程序的提取分支对方案一/二/三处理完全相同：双线性到 2 的幂，再双线性回原尺寸
        size = _round_size(im)
        return Canvas(resize(im, size, KIND_HIGH), _resize_to(im, KIND_HIGH), scheme)
    if scheme == 3:
        size = _round_size(im, CEIL)
        return Canvas(_pad_canvas(im, size, (0, 0, 0)), _resize_to(im, KIND_HIGH), scheme)
    if scheme == 4:
        size = _round_size(im, FLOOR)
        return Canvas(_crop_to_canvas(im, size), _resize_to(im, KIND_HIGH), scheme)
    raise ValueError(f"未知的转换方案编号：{scheme}")


def scheme_infos() -> tuple[SchemeInfo, ...]:
    return SCHEMES


def scheme_names() -> tuple[str, ...]:
    return SCHEME_ITEMS
