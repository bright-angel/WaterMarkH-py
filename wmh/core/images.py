"""图像读入、缩放与 numpy 数组互转。

原程序用 GDI+ 的 Bitmap / Graphics，缩放质量由 InterpolationMode 决定：
  * ``new Bitmap(src, w, h)``        -> 默认双线性（本模块的 KIND_HIGH）
  * ``m_bmp_bmp_int_int`` 显式设置    -> NearestNeighbor（KIND_NEAREST）
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

KIND_HIGH = Image.BILINEAR
KIND_NEAREST = Image.NEAREST

OPEN_ERROR = "无法打开图片文件：{path}"


def load_image(path: str | Path) -> Image.Image:
    """读入并统一成 RGB（原程序 LockBits 只处理 BGR 三通道，Alpha 原样保留）。"""
    path = Path(path)
    try:
        with Image.open(path) as im:
            return im.convert("RGB").copy()
    except FileNotFoundError as exc:  # 保持“文件不存在”语义，交给上层弹窗
        raise FileNotFoundError(OPEN_ERROR.format(path=path)) from exc
    except Exception as exc:
        raise ValueError(OPEN_ERROR.format(path=path)) from exc


def resize(im: Image.Image, size: tuple[int, int], kind: int = KIND_HIGH) -> Image.Image:
    """size 为 (宽, 高)，与 GDI+ DrawImage 的目标矩形一致。"""
    if size == im.size:
        return im.copy()
    return im.resize(size, kind)


def to_array(im: Image.Image) -> np.ndarray:
    """HxWx3 uint8，通道顺序 RGB。算法按平面独立处理，顺序不影响结果。"""
    return np.asarray(im, dtype=np.uint8)


def from_array(data: np.ndarray) -> Image.Image:
    return Image.fromarray(data, "RGB")
