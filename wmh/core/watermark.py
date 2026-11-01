"""水印核心算法：频谱加性嵌入与频谱幅度提取。

对应反编译得到的两个方法：
  m_void_bmp_bmp_string_int_int(Bitmap 画布, Bitmap 水印图, ...) —— 嵌入
  m_void_bmp_string_int_int(Bitmap 画布, ...)                    —— 提取

两者的进度刻度也照搬原程序（原程序每步调用 Invoke(m_void_int_string)）：
  嵌入  0 起点 / 10 读像素 / 20,30,40 三个通道正变换 / 50 叠加 / 60,70,80 逆变换 / 90 写回
  提取  0 起点 / 10 读像素 / 30,50,70 三个通道正变换 / 90 写回
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from . import fft2d

Progress = Callable[[int], None]

BYTES_PER_PIXEL = 3

#: 原程序在嵌入过程中上报的进度刻度（相对本次操作的百分比）
EMBED_STEPS = (0, 10, 20, 30, 40, 50, 60, 70, 80, 90)
#: 提取过程只作正变换，刻度与原程序一致
EXTRACT_STEPS = (0, 10, 30, 50, 70, 90)


def _planes(data: np.ndarray) -> list[np.ndarray]:
    """像素字节 / 256 -> float32 平面（原程序 Format32bppArgb 的三个通道）。"""
    return [data[:, :, channel].astype(np.float32) / 256.0
            for channel in range(data.shape[2])]


def _check_canvas(data: np.ndarray) -> None:
    height, width = data.shape[:2]
    if not (fft2d.is_power_of_two(width) and fft2d.is_power_of_two(height)):
        raise ValueError(
            f"FFT 要求画布宽高均为 2 的整数次幂，当前为 {width}x{height}（T7.IsPowerOfTwo）"
        )


class _Stepper:
    """按固定刻度发回调，避免调用方写错数字。"""

    def __init__(self, steps: tuple[int, ...], progress: Progress | None) -> None:
        self._steps = steps
        self._progress = progress
        self._index = 0

    def tick(self) -> None:
        if self._index >= len(self._steps):
            raise AssertionError("进度刻度用尽，说明算法步骤数量发生变化")
        value = self._steps[self._index]
        self._index += 1
        if self._progress is not None:
            self._progress(value)


def embed(image: np.ndarray, mask: np.ndarray, strength: float,
          progress: Progress | None = None) -> np.ndarray:
    """把水印图（同尺寸、黑底白字）叠加进图像的幅度谱。

    原程序把三个通道记为 array3(R)/array4(G)/array5(B)，每个通道独立做
    ``系数 = 系数 / sqrt(N) + 水印像素 / 256 * 强度``，再整体逆变换。
    """
    if image.shape != mask.shape:
        raise ValueError(f"水印图尺寸必须与画布一致：{image.shape[:2]} != {mask.shape[:2]}")
    _check_canvas(image)
    steps = _Stepper(EMBED_STEPS, progress)

    steps.tick()                                  # 0：锁定 bits / 读取像素
    planes = _planes(image)
    wm_planes = _planes(mask)
    steps.tick()                                  # 10：三个实数平面准备完毕

    spectra = []
    for plane in planes:                          # 20/30/40：逐通道正变换
        steps.tick()
        spectra.append(fft2d.forward(plane))

    strength = float(strength)
    steps.tick()                                  # 50：把水印叠加进频谱
    for spectrum, wm_plane in zip(spectra, wm_planes):
        spectrum += wm_plane * strength

    channels = []
    for spectrum in spectra:                      # 60/70/80：逐通道逆变换
        steps.tick()
        channels.append(fft2d.to_uint8(np.abs(fft2d.backward(spectrum)) * 256.0))

    steps.tick()                                  # 90：写回像素
    return np.stack(channels, axis=-1)


def extract(image: np.ndarray, gain: float, progress: Progress | None = None) -> np.ndarray:
    """只作正向变换，输出幅度谱（乘亮度系数）——水印文字因此可见。"""
    _check_canvas(image)
    steps = _Stepper(EXTRACT_STEPS, progress)

    steps.tick()                                  # 0：锁定 bits / 读取像素
    planes = _planes(image)
    steps.tick()                                  # 10：平面准备完毕

    spectra = []
    for plane in planes:                          # 30/50/70：逐通道正变换
        steps.tick()
        spectra.append(fft2d.forward(plane))

    gain = float(gain)
    channels = [fft2d.to_uint8(np.abs(spectrum) * 256.0 * gain) for spectrum in spectra]
    steps.tick()                                  # 90：写回像素
    return np.stack(channels, axis=-1)
