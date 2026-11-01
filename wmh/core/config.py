"""WaterMarkH.xml 配置读写（原程序用 XmlDocument，路径 Setting/General/OutFormat）。

文件格式保持与原版兼容，因此两个程序可以共用同一个配置文件：
    <?xml version="1.0" encoding="utf-8"?>
    <Setting>
      <General>
        <OutFormat>0</OutFormat>
      </General>
    </Setting>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from . import formats

CONFIG_NAME = "WaterMarkH.xml"
ROOT_TAG = "Setting"
SECTION = "General"
KEY = "OutFormat"


def default_path() -> Path:
    """配置文件位置：开发态沿用 StartupPath，安装态落到用户配置目录。

    可用环境变量 ``WMH_CONFIG`` 强制指定路径（指向 XML 文件本身）。
    """
    override = os.environ.get("WMH_CONFIG")
    if override:
        return Path(override)

    # 开发态（直接从源码运行）：沿用原版“程序所在目录”的约定。
    # 通过项目根目录下的标记文件区分开发与安装态，避免把配置写进 site-packages。
    project_root = Path(__file__).resolve().parents[2]
    if any((project_root / marker).exists() for marker in ("pyproject.toml", "main.py", ".git")):
        return project_root / CONFIG_NAME

    # 安装态：写到用户级配置目录，保证可写且跨运行保留
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "WaterMarkH" / CONFIG_NAME


class Config:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_path()
        self._out_format = formats.JPEG
        self.load()

    # --- 读写 -------------------------------------------------------------
    def load(self) -> None:
        if not self.path.is_file():
            return
        try:
            root = ET.parse(self.path).getroot()
        except ET.ParseError:
            return
        node = root.find(f"{SECTION}/{KEY}")
        if node is None or not (node.text or "").strip():
            return
        try:
            value = int(node.text.strip())
        except ValueError:
            return
        if 0 <= value < len(formats.FORMATS):
            self._out_format = value

    def save(self) -> Path:
        root = None
        if self.path.is_file():
            try:
                root = ET.parse(self.path).getroot()
            except ET.ParseError:
                root = None
        if root is None or root.tag != ROOT_TAG:
            root = ET.Element(ROOT_TAG)
        general = root.find(SECTION)
        if general is None:
            general = ET.SubElement(root, SECTION)
        node = general.find(KEY)
        if node is None:
            node = ET.SubElement(general, KEY)
        node.text = str(self._out_format)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(root).write(self.path, encoding="utf-8", xml_declaration=True)
        return self.path

    # --- 属性 -----------------------------------------------------------
    @property
    def out_format(self) -> int:
        return self._out_format

    @out_format.setter
    def out_format(self, value: int) -> None:
        if not 0 <= int(value) < len(formats.FORMATS):
            raise ValueError(f"未知的输出格式：{value}")
        self._out_format = int(value)

    @property
    def format(self) -> formats.OutputFormat:
        return formats.get(self._out_format)
