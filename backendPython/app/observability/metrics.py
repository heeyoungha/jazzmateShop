import os
import time
from contextlib import contextmanager
from typing import Iterator

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        REGISTRY,
        generate_latest,
        multiprocess,
    )
except ImportError:  # pragma: no cover - local fallback when optional package is absent
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    CollectorRegistry = None
    Counter = None
    Gauge = None
    Histogram = None
    REGISTRY = None
    generate_latest = None
    multiprocess = None


_LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
)


class _NoopMetric:
    def labels(self, **kwargs):
        del kwargs
        return self

    def inc(self, amount: float = 1.0) -> None:
        del amount

    def dec(self, amount: float = 1.0) -> None:
        del amount

    def observe(self, amount: float) -> None:
        del amount


if Histogram is not None:
    recommendation_stage_latency = Histogram(
        "jazzmate_recommendation_stage_duration_seconds",
        "FastAPI recommendation processing stage latency.",
        ("stage", "status"),
        buckets=_LATENCY_BUCKETS,
    )
    recommendation_requests_total = Counter(
        "jazzmate_recommendation_requests_total",
        "FastAPI recommendation requests by terminal status.",
        ("status",),
    )
    recommendation_in_flight = Gauge(
        "jazzmate_recommendation_in_flight",
        "FastAPI recommendation requests currently in flight.",
        multiprocess_mode="livesum",
    )
else:
    recommendation_stage_latency = _NoopMetric()
    recommendation_requests_total = _NoopMetric()
    recommendation_in_flight = _NoopMetric()


@contextmanager
def observe_recommendation_stage(stage: str) -> Iterator[None]:
    started_at = time.monotonic()
    status = "success"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        recommendation_stage_latency.labels(stage=stage, status=status).observe(
            time.monotonic() - started_at
        )


def record_recommendation_completed() -> None:
    recommendation_requests_total.labels(status="completed").inc()


def record_recommendation_failed(error_code: str) -> None:
    recommendation_requests_total.labels(status=f"failed_{error_code.lower()}").inc()


def inc_recommendation_in_flight() -> None:
    recommendation_in_flight.inc()


def dec_recommendation_in_flight() -> None:
    recommendation_in_flight.dec()


def render_prometheus_metrics() -> tuple[bytes, str]:
    if generate_latest is None:
        return b"", CONTENT_TYPE_LATEST

    if os.environ.get("PROMETHEUS_MULTIPROC_DIR") and multiprocess is not None:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry), CONTENT_TYPE_LATEST

    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
