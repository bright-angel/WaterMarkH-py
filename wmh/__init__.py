"""隐形水印工具 V1.2 —— WaterMarkH.exe 的 Python/tkinter 复刻版。

包结构（代码按职责分散在多个模块，入口只有一处）：
  wmh.app            启动入口（创建 Tk root、主窗口、样式）
  wmh.core           与界面无关的算法 / 文件 / 配置逻辑
  wmh.ui             tkinter 界面（主窗口、对话框、控件、主题）
"""

__version__ = "1.2.0.0"
__all__ = ["__version__"]
