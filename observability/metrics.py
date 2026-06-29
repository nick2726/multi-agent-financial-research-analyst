"""Lightweight in-process metrics collector.

This intentionally avoids external dependencies to keep deployment simple.
"""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass
class TimerSample:
    """One timing sample captured in milliseconds."""

    metric_name: str
    duration_ms: float


class InMemoryMetrics:
    """Simple metrics sink for counters and latencies."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = defaultdict(int)
        self._timers: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] += value

    @contextmanager
    def time(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self._timers[name].append(duration_ms)

    def snapshot(self) -> dict[str, object]:
        timer_summary = {}
        for metric_name, values in self._timers.items():
            if not values:
                continue
            timer_summary[metric_name] = {
                "count": len(values),
                "avg_ms": sum(values) / len(values),
                "max_ms": max(values),
                "min_ms": min(values),
            }
        return {
            "counters": dict(self._counters),
            "timers": timer_summary,
        }


metrics = InMemoryMetrics()
