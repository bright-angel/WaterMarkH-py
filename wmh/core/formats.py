"""输出格式与文件名。

原程序按 WaterMarkH.xml 里的 OutFormat 选择 image/jpeg|png|bmp 编码器，
并统一带 Encoder.Quality = 100；文件名是“原文件名_WaterMark.扩展名”，
保存在“保存目录”下。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .constants import OUTPUT_SUFFIX

JPEG = 0
PNG = 1
BMP = 2

JPEG_QUALITY = 100


@dataclass(frozen=True)
class OutputFormat:
    index: int
    name: str          # 与“其它选项”下拉项一致
    extension: str     # 保存时使用的扩展名
    pil_format: str


FORMATS = (
    OutputFormat(JPEG, "JPEG", ".jpg", "JPEG"),
    OutputFormat(PNG, "PNG", ".png", "PNG"),
    OutputFormat(BMP, "BMP", ".bmp", "BMP"),
)


def get(index: int) -> OutputFormat:
    for fmt in FORMATS:
        if fmt.index == index:
            return fmt
    raise ValueError(f"未知的输出格式：{index}")


def output_path(source: str | Path, out_dir: str | Path, index: int) -> Path:
    """<out_dir>/<原文件名>_WaterMark.<扩展名>，与原程序拼接方式一致。"""
    fmt = get(index)
    stem = Path(source).stem
    return Path(out_dir) / f"{stem}{OUTPUT_SUFFIX}{fmt.extension}"


def save(image: Image.Image, path: str | Path, index: int) -> Path:
    fmt = get(index)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = image.convert("RGB")
    params: dict = {}
    if fmt.pil_format == "JPEG":
        # GDI+ 的 Encoder.Quality=100；同时关掉色度二次采样，避免额外损失
        params.update(quality=JPEG_QUALITY, subsampling=0, optimize=False)
    data.save(path, fmt.pil_format, **params)
    return path
