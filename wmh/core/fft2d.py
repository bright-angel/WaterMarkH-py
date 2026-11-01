"""二维 DFT：忠实复刻反编译出的 T7 变换 + 调用方的 sqrt(N) 归一化。

原程序（m_void_bmp_bmp_string_int_int / m_void_bmp_string_int_int）的步骤：
  1. 像素字节 / 256 组成三个实数平面（虚部为 0）；
  2. 对每个平面做**非归一化** 2D 正向 DFT，然后每个系数除以 sqrt(W*H)；
  3. 添加水印：系数 += 水印像素 / 256 * 强度；
  4. 再做**非归一化**反向共轭 DFT，再除以 sqrt(W*H)，取模 * 256 还原像素。

numpy.fft.fft2 的前向变换就是非归一化 DFT，与 T7 的 Forward 完全一致；
numpy.fft.ifft2 自带 1/N，而 T7 的 Backward 不带归一化，所以
``backward()`` 需要把 sqrt(N) 乘回去（N*ifft2(X)/sqrt(N) == sqrt(N)*ifft2(X)）。
两次 sqrt(N) 除法合起来正是“正反都按 1/sqrt(N) 归一化”的单位化变换，
往返一次不会有能量缩放。

变换要求宽高都是 2 的整数次幂（T7.IsPowerOfTwo），方案模块负责凑齐。
"""

from __future__ import annotations

import math

import numpy as np

__all__ = ["is_power_of_two", "forward", "backward", "to_uint8"]


def is_power_of_two(value: int) -> bool:
    return value > 0 and (value & (value - 1)) == 0


def _unitary_scale(count: int) -> float:
    return math.sqrt(float(count))


def forward(plane: np.ndarray) -> np.ndarray:
    """非归一化 2D DFT 后再除以 sqrt(N)（等价于单位化正变换）。"""
    spectrum = np.fft.fft2(plane)
    return spectrum / _unitary_scale(plane.size)


def backward(spectrum: np.ndarray) -> np.ndarray:
    """非归一化 2D 反向 DFT 后再除以 sqrt(N)（等价于单位化逆变换）。"""
    return np.fft.ifft2(spectrum) * _unitary_scale(spectrum.shape[0] * spectrum.shape[1])


def to_uint8(values: np.ndarray) -> np.ndarray:
    """复刻 (byte)Math.Max(0, Math.Min(255, (int)float)) —— 向零截断后夹取。"""
    truncated = np.trunc(values.astype(np.float32, copy=False))
    return np.clip(truncated, 0.0, 255.0).astype(np.uint8)
