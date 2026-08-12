"""Trace recording and report building.

Everything a framework emits -- handover events, step outcomes, session
snapshots -- is recorded and aggregated here so an evaluation can be shared
or audited as JSON or Markdown.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from .core.types import HandoverEvent, TaskOutcome
from .mediators import MetricResult

class TraceRecorder:
    """Collects events from one or many framework runs."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._runs: list[dict[str, Any]] = []

    def attach(self, framework) -> "TraceRecorder":
        """Subscribe to a framework's handover events."""

        def _on_event(event: HandoverEvent, _ctx) -> None:
            self._events.append(
                {
                    "event_id": event.event_id,
                    "timestamp": event.timestamp,
                    "direction": event.direction.value,
                    "trigger": event.trigger.value,
                    "outcome": event.outcome.value,
                    "step_id": event.step_id,
                    "reason": event.reason,
                    "duration": event.duration,
                }
            )

        framework.add_observer(_on_event)
        return self

    def record_outcome(self, outcome: TaskOutcome) -> None:
        self._runs.append(
            {
                "task_id": outcome.task.id,
                "elapsed": outcome.elapsed,
                "successful": outcome.successful,
                "n_steps": outcome.n_steps,
                "passed_steps": outcome.passed_steps,
                "n_handovers": outcome.n_handovers,
            }
        )

    def export(self) -> dict[str, Any]:
        return {"events": self._events, "runs": self._runs}

    def to_json(self, path: Optional[str] = None) -> str:
        text = json.dumps(self.export(), indent=2, default=str)
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        return text


@dataclass
class RunResult:
    """One task executed once through a framework, fully evaluated."""

    framework_name: str
    task_id: str
    outcome: TaskOutcome
    mediators: dict[str, MetricResult] = field(default_factory=dict)
    performance: dict[str, MetricResult] = field(default_factory=dict)

    def scores(self) -> dict[str, float]:
        return {
            key: m.value for key, m in {**self.mediators, **self.performance}.items()
        }


@dataclass
class EvaluationReport:
    """Aggregated results across runs."""

    framework_name: str
    runs: list[RunResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def n_runs(self) -> int:
        return len(self.runs)

    def aggregated(self) -> dict[str, float]:
        """Mean value of every measured key across runs."""
        agg: dict[str, float] = {}
        for run in self.runs:
            for key, value in run.scores().items():
                agg[key] = agg.get(key, 0.0) + value
        if self.runs:
            for key in agg:
                agg[key] /= len(self.runs)
        return agg

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework": self.framework_name,
            "metadata": self.metadata,
            "n_runs": self.n_runs,
            "aggregated": self.aggregated(),
            "runs": [
                {
                    "task": r.task_id,
                    "elapsed": r.outcome.elapsed,
                    "successful": r.outcome.successful,
                    "n_handovers": r.outcome.n_handovers,
                    "mediators": {k: m.value for k, m in r.mediators.items()},
                    "performance": {k: m.value for k, m in r.performance.items()},
                }
                for r in self.runs
            ],
        }

    def to_json(self, path: Optional[str] = None) -> str:
        text = json.dumps(self.to_dict(), indent=2, default=str)
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        return text

    def to_markdown(self, path: Optional[str] = None) -> str:
        """Render a human-friendly report."""
        lines: list[str] = []
        lines.append(f"# Evaluation report: {self.framework_name}")
        lines.append("")
        for k, v in self.metadata.items():
            lines.append(f"- **{k}**: {v}")
        lines.append(f"- **runs**: {self.n_runs}")
        lines.append("")
        lines.append("## Aggregated scores")
        lines.append("")
        lines.append("| metric | mean | direction |")
        lines.append("|--------|------|-----------|")
        for key, value in sorted(self.aggregated().items()):
            lines.append(f"| {key} | {value:.3f} | - |")
        lines.append("")
        lines.append("## Per run")
        lines.append("")
        lines.append("| run | task | elapsed | handovers | pass |")
        lines.append("|-----|------|---------|-----------|------|")
        for i, run in enumerate(self.runs, start=1):
            lines.append(
                f"| {i} | {run.task_id} | {run.outcome.elapsed:.2f}s | "
                f"{run.outcome.n_handovers} | {run.outcome.passed_steps}/{run.outcome.n_steps} |"
            )
        lines.append("")
        text = "\n".join(lines)
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        return text
