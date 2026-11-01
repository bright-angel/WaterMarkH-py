"""算法与业务逻辑（与界面无关，可单独自测）。

模块划分：
  constants   界面文案 / 方案说明 / 数值范围
  fft2d       二维 DFT（复刻非归一化变换 + sqrt(N) 归一化）
  watermark   频谱加性嵌入与幅度谱提取
  schemes     五种转换方案（补齐 2 的整数次幂画布并还原）
  textmask    水印文字掩膜（黑底白字 + 180° 旋转）
  fonts       字体族名到 TrueType 文件的解析
  images      读图、缩放、数组互转
  formats     JPEG/PNG/BMP 输出与 _WaterMark 文件名
  config      WaterMarkH.xml 读写
  pipeline    端到端流程（含原程序的进度百分比节奏）
  worker      后台线程与主线程消息回灌
"""

from .config import Config
from .pipeline import AddResult, add_watermark, extract_watermark
from .textmask import FontSpec

__all__ = ["Config", "FontSpec", "AddResult", "add_watermark", "extract_watermark"]
