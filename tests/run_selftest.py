"""统一自测入口：不依赖 pytest，直接跑完所有 ``test_*`` 函数。

用法：
    python tests/run_selftest.py              全部执行
    python tests/run_selftest.py fft          只跑名字里含 fft 的用例
    python tests/run_selftest.py test_gui     只跑界面用例
"""

from __future__ import annotations

import importlib
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MODULES = ("tests.test_core", "tests.test_worker", "tests.test_gui")


def _tests(module) -> list:
    return [(name, getattr(module, name)) for name in sorted(vars(module))
            if name.startswith("test_") and callable(getattr(module, name))]


def main(argv: list[str]) -> int:
    filter_text = argv[0] if argv else ""
    passed: list[str] = []
    failed: list[tuple[str, str]] = []

    for module_name in MODULES:
        module = importlib.import_module(module_name)
        for name, function in _tests(module):
            label = f"{module_name}.{name}"
            if filter_text and filter_text not in label:
                continue
            start = time.perf_counter()
            try:
                function()
            except BaseException:  # noqa: BLE001 - 记录任何失败
                failed.append((label, traceback.format_exc()))
                print(f"[FAIL] {label}")
            else:
                elapsed = time.perf_counter() - start
                passed.append(label)
                print(f"[ OK ] {label}  ({elapsed:.2f}s)")

    for label, trace in failed:
        print(f"\n===== {label} =====\n{trace}", end="")

    print(f"\n合计 {len(passed) + len(failed)} 项，通过 {len(passed)}，失败 {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
