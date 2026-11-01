# WaterMarkH-py

隐形水印工具 **WaterMarkH** 的 Python / tkinter 复刻版。在图像频域（频谱）中嵌入与提取文本水印，水印对人眼基本不可见，可用于版权溯源与完整性校验。

> 版本：`1.2.0.0`（与 `wmh/__init__.py` 中的 `__version__` 保持一致）

## 功能特性

- **频域加性嵌入**：基于二维 DFT，在幅度谱上叠加旋转后的文字掩膜，原图视觉几乎无变化。
- **水印提取**：无需原图，直接对带水印图做逆过程提取出文字。
- **五种转换方案**：自动补齐到 2 的整数次幂画布并还原，适配不同尺寸输入。
- **多种输出格式**：JPEG / PNG / BMP，质量与原版一致（JPEG 质量 100、关闭色度二次采样）。
- **中文友好**：内置 Windows 常见中文字体映射（黑体 / 微软雅黑 / 宋体等）。
- **图形界面**：基于 tkinter，操作与原版一致——选择图片、设置水印文字、嵌入或提取。

## 安装

本项目已改造为可用 `uv tool` 安装的标准 Python 包。

### 方式一：从源码目录安装（开发 / 本地）

```bash
cd WaterMarkH-py
uv tool install .
```

### 方式二：从构建好的 wheel 安装

```bash
uv build                      # 生成 dist/*.whl 与 dist/*.tar.gz
uv tool install ./dist/watermarkh-1.2.0.0-py3-none-any.whl
```

### 方式三：从 PyPI / Git 安装（发布后）

```bash
uv tool install watermarkh
```

> 安装后会在 uv 的工具目录下生成可执行入口 `watermarkh`。
> 若 `watermarkh` 不在 PATH 中，可用 `uvx watermarkh` 或 `uv tool run watermarkh` 启动。

## 使用

```bash
watermarkh          # 启动图形界面
```

界面中：

- **嵌入水印（添加）**：选择源图片 → 输入水印文字 → 选择输出目录 → 点击“添加水印”。
  生成的文件名为 `<原文件名>_WaterMark.<扩展名>`，保存在输出目录。
- **提取水印（获取）**：选择带水印的图片 → 点击“获取水印”，文字会显示在结果区。

也可不安装、直接从源码运行（需已激活含 numpy / Pillow 的虚拟环境）：

```bash
python main.py
```

## 配置

配置文件 `WaterMarkH.xml` 与原版格式兼容，可共用：

```xml
<?xml version="1.0" encoding="utf-8"?>
<Setting>
  <General>
    <OutFormat>0</OutFormat>   <!-- 0=JPEG, 1=PNG, 2=BMP -->
  </General>
</Setting>
```

- **开发态**（从源码运行）：配置文件位于项目根目录。
- **安装态**：配置文件位于用户目录
  - Windows：`%APPDATA%\WaterMarkH\WaterMarkH.xml`
  - macOS：`~/Library/Application Support/WaterMarkH/WaterMarkH.xml`
  - Linux：`~/.config/watermarkh/WaterMarkH.xml`

### 环境变量

| 变量 | 作用 |
| --- | --- |
| `WMH_CONFIG` | 强制指定配置文件（XML 文件本身）的绝对路径，覆盖默认位置。 |
| `WMH_FONT_DIR` | 手动指定字体搜索目录（非 Windows 或字体不在系统目录时使用）。 |

## 测试

```bash
python tests/run_selftest.py     # 跑一遍算法自测（含 GUI 冒烟）
```

测试套件位于 `tests/`：`test_core.py`（算法 / 流程）、`test_gui.py`、`test_worker.py`。

## 依赖与环境

- **Python**：≥ 3.9
- **第三方依赖**：`numpy>=1.26`、`Pillow>=10.0`
- **GUI 运行时**：`tkinter`（Python 标准库，需系统提供 Tcl/Tk）
  - 通过 `uv tool install` 安装时，uv 自带管理的 Python 已内置 Tcl/Tk（Windows 上实测为 Tk 8.6），开箱即用。
  - 若使用其他 Python 发行版，请确保其包含 Tk（如系统缺失 Tcl/Tk，运行时会报 `import tkinter` 错误）。

## 项目结构

```
WaterMarkH-py/
├── pyproject.toml          # 包元数据与构建配置（uv tool 安装入口）
├── main.py                 # 源码直接运行入口
├── wmh/
│   ├── __init__.py         # 版本号
│   ├── app.py              # 应用启动（Tk root、图标、DPI）
│   ├── assets/app.ico      # 图标（随包分发）
│   ├── core/               # 算法与业务逻辑（与界面无关，可单独自测）
│   │   ├── fft2d.py        # 二维 DFT
│   │   ├── watermark.py    # 频谱嵌入 / 幅度谱提取
│   │   ├── schemes.py      # 五种转换方案
│   │   ├── textmask.py     # 文字掩膜（黑底白字 + 180° 旋转）
│   │   ├── fonts.py        # 字体族名 -> TTF/TTC 解析
│   │   ├── images.py       # 读图 / 缩放 / 数组互转
│   │   ├── formats.py      # 输出格式与文件名
│   │   ├── config.py       # WaterMarkH.xml 读写
│   │   ├── pipeline.py     # 端到端流程
│   │   └── worker.py       # 后台线程
│   └── ui/                 # tkinter 界面
│       ├── main_window.py  # 主窗口
│       ├── options_dialog.py
│       ├── font_dialog.py
│       ├── about_dialog.py
│       ├── preview.py
│       ├── theme.py
│       └── widgets.py
└── tests/                  # 自测
```
