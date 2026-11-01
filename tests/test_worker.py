"""后台任务调度（TaskRunner）自测：进度回灌、成功/失败分发、并发保护。"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wmh.core.worker import TaskRunner  # noqa: E402


class ManualScheduler:
    """替代 tkinter.Tk：after() 只登记回调，由测试手动驱动“事件循环”。"""

    def __init__(self) -> None:
        self.pending: list = []

    def after(self, delay_ms: int, func, *args) -> None:  # noqa: ANN401
        self.pending.append(lambda: func(*args))

    def spin(self, runner: TaskRunner, timeout: float = 20.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            while self.pending:
                self.pending.pop(0)()
            if not runner.busy and not self.pending:
                return
            time.sleep(0.005)
        raise TimeoutError("后台任务未在预期时间内结束")


def test_worker_delivers_progress_and_result() -> None:
    scheduler = ManualScheduler()
    runner = TaskRunner(scheduler, poll_ms=1)
    progress: list[tuple[int, str]] = []
    done: list[str] = []
    errors: list[BaseException] = []

    def work(report) -> str:
        report(10, "正在添加 10%")
        report(90, "正在添加 90%")
        return "ok"

    assert runner.submit(work, on_progress=lambda p, m: progress.append((p, m)),
                         on_success=done.append, on_failure=errors.append)
    scheduler.spin(runner)
    assert progress == [(10, "正在添加 10%"), (90, "正在添加 90%")]
    assert done == ["ok"] and errors == []
    assert not runner.busy


def test_worker_reports_exception() -> None:
    scheduler = ManualScheduler()
    runner = TaskRunner(scheduler, poll_ms=1)
    failures: list[BaseException] = []

    def work(_report) -> None:
        raise ValueError("参数不对")

    assert runner.submit(work, on_failure=failures.append)
    scheduler.spin(runner)
    assert len(failures) == 1 and isinstance(failures[0], ValueError)


def test_worker_refuses_concurrent_jobs() -> None:
    scheduler = ManualScheduler()
    runner = TaskRunner(scheduler, poll_ms=1)
    gate = threading.Event()
    release = threading.Event()

    def work(_report) -> str:
        gate.set()
        release.wait(10)
        return "slow"

    assert runner.submit(work)
    gate.wait(5)
    assert runner.busy
    assert runner.submit(lambda _r: "second") is False, "任务运行期间应拒绝新任务"
    release.set()
    scheduler.spin(runner)
    assert not runner.busy


def test_worker_runs_off_the_ui_thread() -> None:
    scheduler = ManualScheduler()
    runner = TaskRunner(scheduler, poll_ms=1)
    main_thread = threading.get_ident()
    seen: dict[str, int] = {}

    def work(_report) -> int:
        return threading.get_ident()

    assert runner.submit(work, on_success=lambda ident: seen.update(thread=ident))
    scheduler.spin(runner)
    assert seen["thread"] != main_thread, "耗时计算不得在主线程执行"
