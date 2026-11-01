"""隐形水印工具 V1.2（Python / tkinter 复刻版）程序入口。

用法：
    python main.py                 启动图形界面
    python tests/run_selftest.py    跑一遍算法自测（含 GUI 冒烟）
"""

from __future__ import annotations


def main() -> int:
    from wmh.app import run
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
