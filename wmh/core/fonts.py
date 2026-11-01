"""字体名 -> 可渲染字形文件（TrueType/OpenType）的解析。

原程序用 GDI+ 的 FontDialog，默认字体是“黑体 9.75pt”。Pillow 需要显式的
字体文件路径，所以这里维护一份 Windows 常见中文字体映射，并允许按目录扫描。
"""

from __future__ import annotations

import os
from pathlib import Path

_FONT_DIRS: tuple[Path, ...] = ()

#: 字体族名 -> 候选文件名（按顺序尝试）
CANDIDATES: dict[str, tuple[str, ...]] = {
    "黑体": ("simhei.ttf", "simhei.ttc"),
    "宋体": ("simsun.ttc", "simsun.ttf"),
    "微软雅黑": ("msyh.ttc", "msyh.ttf"),
    "Microsoft YaHei": ("msyh.ttc", "msyh.ttf"),
    "Microsoft YaHei UI": ("msyh.ttc", "msyh.ttf"),
    "仿宋": ("simfang.ttf", "simfangb.ttf"),
    "楷体": ("simkai.ttf", "kaiti.ttf"),
    "隶书": ("SIMLI.TTF", "simli.ttf"),
    "幼圆": ("SIMYOU.TTF", "simyou.ttf"),
    "Arial": ("arial.ttf",),
    "Times New Roman": ("times.ttf",),
}

#: 兜底顺序：优先能显示中文的字体
FALLBACKS = ("simhei.ttf", "msyh.ttc", "simsun.ttc", "arial.ttf")

_POINT_TO_PIXEL = 96.0 / 72.0


def font_dirs() -> tuple[Path, ...]:
    """返回本机的字体搜索目录（Windows 字体目录 + 环境变量覆盖）。"""
    global _FONT_DIRS
    if _FONT_DIRS:
        return _FONT_DIRS
    dirs: list[Path] = []
    override = os.environ.get("WMH_FONT_DIR")
    if override:
        dirs.append(Path(override))
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    dirs.append(windir / "Fonts")
    dirs.append(Path(r"C:\Windows\Fonts"))
    _FONT_DIRS = tuple(dict.fromkeys(d for d in dirs if d.is_dir())) or tuple(dirs)
    return _FONT_DIRS


def set_font_dirs(*dirs: str | Path) -> None:
    """测试或非 Windows 环境下手动指定字体目录。"""
    global _FONT_DIRS
    _FONT_DIRS = tuple(Path(d) for d in dirs)


def point_to_pixels(point: float) -> int:
    """GDI+ 以磅为单位，Pillow 以像素为单位（96 DPI）。"""
    return max(1, int(round(float(point) * _POINT_TO_PIXEL)))


def _find_file(name: str) -> Path | None:
    wanted = name.lower()
    for directory in font_dirs():
        if not directory.is_dir():
            continue
        for candidate in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            if candidate.name.lower() == wanted:
                return candidate
    return None


def resolve_path(family: str) -> Path:
    """把字体族名解析成磁盘上的字体文件。"""
    for name in (*CANDIDATES.get(family, ()), f"{family}.ttf", f"{family}.ttc", f"{family}.otf"):
        found = _find_file(name)
        if found is not None:
            return found
    for name in FALLBACKS:
        found = _find_file(name)
        if found is not None:
            return found
    raise FileNotFoundError(
        "未找到可用的 TrueType 字体，无法渲染水印文字。"
        "请安装“黑体/微软雅黑”，或用环境变量 WMH_FONT_DIR 指定字体目录。"
    )
