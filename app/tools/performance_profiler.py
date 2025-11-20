"""
performance_profiler: A production-ready profiling decorator tool.

TOOL NAME: performance_profiler
PURPOSE: Measure execution time, CPU usage, and memory footprint of a Python function call.
CATEGORY: utility

This module exposes a decorator factory function `performance_profiler` that can be used as:

- As a decorator with parameters: @performance_profiler(sample_interval=0.05)
- As a bare decorator: @performance_profiler
- As a regular callable to get the decorator: performance_profiler()(func)

It prints function name, execution time (seconds), peak memory usage (MiB), and average CPU load (%)
for the wrapped call.
"""
from __future__ import annotations

import os
import threading
import time
from functools import wraps
from typing import Any, Callable, List, Optional, Tuple, TypeVar, ParamSpec, Union, overload

# Attempt to import psutil. Provide graceful degradation if missing.
try:
    import psutil  # type: ignore
    _PSUTIL_AVAILABLE = True
except Exception:  # pragma: no cover - environment dependent
    psutil = None  # type: ignore
    _PSUTIL_AVAILABLE = False

# smolagents tool decorator - provide a lightweight fallback if smolagents is not installed
try:  # pragma: no cover - environment dependent
    from smolagents import tool  # type: ignore
except Exception:  # pragma: no cover - environment dependent
    def tool(func: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore
        """Fallback no-op decorator if smolagents.tool is unavailable.

        Args:
            func: Function to decorate.
        Returns:
            The function unchanged.
        """
        return func


P = ParamSpec("P")
R = TypeVar("R")


class _Sampler:
    """Background sampler for process CPU usage and memory RSS using psutil.

    Samples at a specified interval until stopped. Tracks average CPU percent and
    peak RSS memory (bytes) observed.
    """

    def __init__(self, sample_interval: float) -> None:
        if not _PSUTIL_AVAILABLE:
            raise RuntimeError(
                "psutil is required for CPU and memory sampling. Please install it via 'pip install psutil'."
            )
        if sample_interval <= 0:
            raise ValueError("sample_interval must be > 0 seconds")
        self.sample_interval = float(sample_interval)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._cpu_samples: List[float] = []
        self._peak_rss: int = 0
        self._proc = psutil.Process(os.getpid())  # type: ignore[attr-defined]

    def _run(self) -> None:
        # Repeatedly sample CPU percent over the interval and RSS memory.
        while not self._stop_event.is_set():
            try:
                cpu = self._proc.cpu_percent(interval=self.sample_interval)
                rss = self._proc.memory_info().rss
                self._cpu_samples.append(float(cpu))
                if rss > self._peak_rss:
                    self._peak_rss = int(rss)
            except Exception:
                # In case of transient psutil errors, continue sampling.
                pass

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="performance_profiler_sampler", daemon=True)
        self._thread.start()

    def stop(self) -> Tuple[float, int]:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.sample_interval * 2)
        # Compute average CPU percent; if no samples were collected, return 0.0
        avg_cpu = float(sum(self._cpu_samples) / len(self._cpu_samples)) if self._cpu_samples else 0.0
        return avg_cpu, self._peak_rss


@tool
def performance_profiler(
    func: Optional[Callable[P, R]] = None,
    *,
    sample_interval: float = 0.05,
    print_results: bool = True,
) -> Union[Callable[P, R], Callable[[Callable[P, R]], Callable[P, R]]]:
    """A decorator (tool) that profiles execution time, CPU usage, and peak memory.

    This function can be used as a decorator with or without parameters.

    Usage examples:
        @performance_profiler
        def my_func(...):
            ...

        @performance_profiler(sample_interval=0.02)
        def my_func(...):
            ...

    Args:
        func: Optional function to decorate when used as a bare decorator. If None,
            the function returns a decorator configured by the provided parameters.
        sample_interval: Sampling interval in seconds for CPU and memory monitoring.
            Must be greater than 0. Smaller values provide finer granularity at
            the cost of slightly higher overhead. Default is 0.05 seconds.
        print_results: Whether to print the profiling results to stdout. Defaults to True.

    Returns:
        - If used as @performance_profiler: the wrapped function with profiling enabled.
        - If used as @performance_profiler(...): a decorator that can be applied to a function.

    Raises:
        ValueError: If sample_interval is not greater than 0.
        TypeError: If `func` is provided but is not callable.
        RuntimeError: If psutil is required but not installed. Timing will still work,
            but CPU/memory metrics will be shown as N/A when psutil is missing.
    """

    if sample_interval <= 0:
        raise ValueError("sample_interval must be > 0 seconds")

    if func is not None and not callable(func):
        raise TypeError("The first argument to performance_profiler must be a callable or None.")

    def _decorator(target: Callable[P, R]) -> Callable[P, R]:
        if not callable(target):
            raise TypeError("@performance_profiler can only be applied to callables")

        @wraps(target)
        def _wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            start_time = time.perf_counter()
            sampler: Optional[_Sampler] = None
            avg_cpu: float = 0.0
            peak_rss: int = 0

            # Start sampler if psutil is available
            if _PSUTIL_AVAILABLE:
                try:
                    sampler = _Sampler(sample_interval)
                    sampler.start()
                except Exception:
                    sampler = None  # Degrade gracefully if sampling cannot start

            result: R
            exc: Optional[BaseException] = None
            try:
                result = target(*args, **kwargs)
            except BaseException as e:  # Capture any exception to still report metrics
                exc = e
                raise
            finally:
                # Stop timer and sampler
                end_time = time.perf_counter()
                if sampler is not None:
                    try:
                        avg_cpu, peak_rss = sampler.stop()
                    except Exception:
                        avg_cpu, peak_rss = 0.0, 0

                elapsed = end_time - start_time

                if print_results:
                    func_name = getattr(target, "__qualname__", getattr(target, "__name__", str(target)))
                    peak_mib = (peak_rss / (1024 * 1024)) if peak_rss else 0.0
                    cpu_str = f"{avg_cpu:.2f}%" if _PSUTIL_AVAILABLE else "N/A"
                    mem_str = f"{peak_mib:.3f} MiB" if _PSUTIL_AVAILABLE else "N/A"
                    status = "OK" if exc is None else f"ERROR: {type(exc).__name__}"
                    print(
                        f"[performance_profiler] function={func_name} status={status} "
                        f"time_sec={elapsed:.6f} avg_cpu={cpu_str} peak_mem={mem_str}"
                    )

            return result

        return _wrapped

    # If used directly as @performance_profiler
    if func is not None:
        return _decorator(func)

    # If used as @performance_profiler(...)
    return _decorator


__all__ = ["performance_profiler"]