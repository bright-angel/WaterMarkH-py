"""后台任务：把耗时的 FFT 计算放到工作线程，进度与结果回灌主线程。

原程序用 ``new Thread(...) { IsBackground = true }`` 加 ``Invoke(...)`` 委托；
这里等价实现为：工作线程只往队列里投递消息，主线程用 ``root.after`` 轮询取出。
本模块不直接依赖 tkinter —— 只要传入的对象有 ``after(ms, callback)`` 即可。
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
from collections.abc import Callable
from typing import Any, Protocol

from .pipeline import Progress

Work = Callable[[Progress], Any]


class Scheduler(Protocol):
    """能延迟调用回调的对象（tkinter.Tk 即满足）。"""

    def after(self, delay_ms: int, func: Callable[[], Any], *args: Any) -> Any: ...


POLL_INTERVAL_MS = 40


class TaskRunner:
    """一次只跑一个任务；运行期间 ``busy`` 为真，界面对应禁用两个选项卡。"""

    def __init__(self, scheduler: Scheduler, poll_ms: int = POLL_INTERVAL_MS) -> None:
        self._scheduler = scheduler
        self._poll_ms = poll_ms
        self._queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._pending_messages = 0
        self._thread: threading.Thread | None = None
        self._handlers: tuple[Progress, Callable[[Any], None], Callable[[BaseException], None]] = (
            lambda *_: None, lambda *_: None, lambda *_: None)
        self._scheduled = False
        self._running = False
        self._cancelled = False

    # --- 状态 -----------------------------------------------------------
    @property
    def busy(self) -> bool:
        """任务是否还在跑。

        用标志位而不是 ``thread.is_alive()``：``Thread.start()`` 返回后线程可能
        还没来得及被调度，此刻 ``is_alive()`` 仍为 False，界面会漏掉一帧禁用状态。
        """
        return self._running

    def is_idle(self) -> bool:
        """线程已结束且队列里的结果都已回灌主线程（界面测试与关闭时用）。"""
        return not self._running and not self._pending_messages

    # --- 投递与消费 -----------------------------------------------------
    # 计数器只由工作线程 +1、主线程 -1，CPython 的 GIL 保证单次加减是原子的。
    def _post(self, kind: str, payload: Any) -> None:
        self._queue.put((kind, payload))
        self._pending_messages += 1

    def _consume(self) -> tuple[str, Any]:
        kind, payload = self._queue.get_nowait()
        self._pending_messages -= 1
        return kind, payload

    # --- 提交 -----------------------------------------------------------
    def submit(self, work: Work,
               on_progress: Progress | None = None,
               on_success: Callable[[Any], None] | None = None,
               on_failure: Callable[[BaseException], None] | None = None) -> bool:
        """提交任务；若已有任务在跑则返回 False（原程序靠禁用选项卡达到同样效果）。"""
        if self._running:
            return False
        self._handlers = (on_progress or (lambda *_: None),
                          on_success or (lambda *_: None),
                          on_failure or (lambda *_: None))
        self._cancelled = False
        self._running = True
        self._thread = threading.Thread(target=self._run, args=(work,), daemon=True)
        self._thread.start()
        self._schedule()
        return True

    # --- 线程体 ---------------------------------------------------------
    def _run(self, work: Work) -> None:
        def progress(percent: int, message: str) -> None:
            self._post("progress", (percent, message))

        try:
            result = work(progress)
        except BaseException as exc:  # noqa: BLE001 - 与原程序 catch(Exception) 同级
            self._post("error", (exc, traceback.format_exc()))
        else:
            self._post("done", result)

    # --- 主线程泵 -------------------------------------------------------
    def _schedule(self) -> None:
        if self._scheduled or self._cancelled:
            return
        self._scheduled = True
        # 主窗口销毁后 after() 会抛 TclError，此时只需停止泵送，任务线程本身是 daemon。
        try:
            self._scheduler.after(self._poll_ms, self._pump)
        except Exception:  # noqa: BLE001 - 解释器已销毁
            self._scheduled = False
            self._cancelled = True

    def cancel(self) -> None:
        """关闭窗口时调用：停止轮询，不再向已销毁的界面回灌结果。"""
        self._cancelled = True

    def _pump(self) -> None:
        self._scheduled = False
        if self._cancelled:
            return
        finished = self._dispatch()
        if not finished:
            self._schedule()

    def _dispatch(self) -> bool:
        """取出队列里所有消息并回调；返回 True 表示任务已结束。"""
        on_progress, on_success, on_failure = self._handlers
        finished = False
        while not finished:
            try:
                kind, payload = self._consume()
            except queue.Empty:
                break
            if kind == "progress":
                on_progress(*payload)
            elif kind == "done":
                finished = True
                self._running = False
                on_success(payload)
            elif kind == "error":
                finished = True
                self._running = False
                exc, trace = payload
                on_failure(exc)
                if trace:
                    print(trace, flush=True)
        return finished

    def drain(self, timeout: float = 120.0, interval: float = 0.01) -> None:
        """无事件循环时同步跑完当前任务（供自测脚本使用）。"""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._dispatch():
                return
            if self._thread is None:
                return
            time.sleep(interval)
        raise TimeoutError("后台任务超时未结束")
