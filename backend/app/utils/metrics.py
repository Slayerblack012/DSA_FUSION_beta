"""
DSA AutoGrader - Metrics (Prometheus).

Lightweight metrics without prometheus_client dependency.
"""

import logging
from collections import defaultdict, deque
from typing import Dict, Optional

logger = logging.getLogger("dsa.metrics")


class SimpleMetrics:
    """Simple in-memory metrics collector."""

    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
        self.histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.gauges: Dict[str, float] = {}

    def inc(self, name: str, value: int = 1, labels: Optional[Dict] = None):
        """Increment counter."""
        key = self._make_key(name, labels)
        self.counters[key] += value

    def observe(self, name: str, value: float, labels: Optional[Dict] = None):
        """Observe histogram value."""
        key = self._make_key(name, labels)
        self.histograms[key].append(value)

    def set(self, name: str, value: float, labels: Optional[Dict] = None):
        """Set gauge value."""
        key = self._make_key(name, labels)
        self.gauges[key] = value

    def _make_key(self, name: str, labels: Optional[Dict] = None) -> str:
        """Make metric key with labels."""
        if labels:
            labels_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{labels_str}}}"
        return name

    def generate_text(self) -> str:
        """Generate Prometheus-format text."""
        lines = []

        # Counters
        for key, value in self.counters.items():
            lines.append(f"# TYPE {key.split('{')[0]} counter")
            lines.append(f"{key} {value}")

        # Histograms (simplified)
        for key, values in self.histograms.items():
            base_name = key.split("{")[0]
            lines.append(f"# TYPE {base_name} histogram")
            if values:
                # Fix: Prometheus requires NUMERIC values (not quoted strings)
                lines.append(f'{base_name}_sum{{}} {sum(values):.2f}')
                lines.append(f'{base_name}_count{{}} {len(values)}')
                lines.append(
                    f'{base_name}_bucket{{le="0.5"}} {sum(1 for v in values if v <= 0.5)}'
                )
                lines.append(
                    f'{base_name}_bucket{{le="1.0"}} {sum(1 for v in values if v <= 1.0)}'
                )
                lines.append(f'{base_name}_bucket{{le="+Inf"}} {len(values)}')

        # Gauges
        for key, value in self.gauges.items():
            lines.append(f"# TYPE {key.split('{')[0]} gauge")
            lines.append(f"{key} {value}")

        return "\n".join(lines)


# Global metrics instance
metrics = SimpleMetrics()


def generate_metrics() -> str:
    """Generate metrics text."""
    return metrics.generate_text()


class MetricsMiddleware:
    """Simple metrics middleware (placeholder)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Pass through without metrics collection
        await self.app(scope, receive, send)


# Convenience functions
def record_job_start():
    metrics.inc("dsa_jobs_total", labels={"status": "started"})
    metrics.set("dsa_active_jobs", 1)


def record_job_complete(duration: float):
    metrics.inc("dsa_jobs_total", labels={"status": "completed"})
    metrics.set("dsa_active_jobs", 0)
    metrics.observe("dsa_job_duration_seconds", duration)


def record_ai_call(provider: str, status: str, latency: float, tokens: Dict = None):
    metrics.inc("dsa_ai_calls_total", labels={"provider": provider, "status": status})
    metrics.observe("dsa_ai_latency_seconds", latency, labels={"provider": provider})


def record_plagiarism_check(detected: bool):
    metrics.inc("dsa_plagiarism_checks_total")
    if detected:
        metrics.inc("dsa_plagiarism_detected_total")
