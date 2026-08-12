"""Performance metrics (the DV of the model).

Quality, efficiency and safety. Like mediators, these are open -- subclass
:class:`PerformanceMetric` and register it in a
:class:`~crusaders.performance.MetricSet`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..core.types import Role, TaskOutcome
from ..mediators import MetricResult
from ..metaknowledge import OrganizationalMetaknowledge


class PerformanceMetric(ABC):
    """Base class for a performance (dependent-variable) metric."""

    key: str = "metric"
    label: str = "Metric"
    higher_is_better: bool = True

    def __init__(self, metaknowledge: Optional[OrganizationalMetaknowledge] = None) -> None:
        self.metaknowledge = metaknowledge

    @abstractmethod
    def compute(self, outcome: TaskOutcome) -> MetricResult: ...


class QualityMetric(PerformanceMetric):
    """Pass rate, mean decision quality and AI vs expert quality split."""

    key = "quality"
    label = "Quality"
    higher_is_better = True

    def compute(self, outcome: TaskOutcome) -> MetricResult:
        passed = sum(1 for o in outcome.step_outcomes if o.passed)
        rate = passed / outcome.n_steps if outcome.n_steps else 0.0
        qualities = [o.decision.quality_estimate for o in outcome.step_outcomes]
        mean_q = sum(qualities) / len(qualities) if qualities else 0.0
        return MetricResult(
            key=self.key,
            value=rate,
            label=self.label,
            higher_is_better=self.higher_is_better,
            series=qualities,
            detail={
                "pass_rate": rate,
                "passed": passed,
                "total": outcome.n_steps,
                "mean_quality": mean_q,
            },
        )


class EfficiencyMetric(PerformanceMetric):
    """Time efficiency vs the ideal, plus the human-cost share.

    ``time_efficiency`` is capped at 1.0 (you can never beat the ideal by
    much; anything above is treated as the ceiling). The value reported is
    time efficiency.
    """

    key = "efficiency"
    label = "Efficiency"
    higher_is_better = True

    def __init__(self, ideal_time: Optional[float] = None) -> None:
        super().__init__()
        self._ideal = ideal_time

    def compute(self, outcome: TaskOutcome) -> MetricResult:
        ideal = self._ideal or outcome.task.ideal_time
        if ideal is None:
            # fall back to: time AI would need alone (cheap) + expert at speed
            ideal = sum(o.decision.latency for o in outcome.step_outcomes)
        efficiency = min(1.0, ideal / outcome.elapsed) if outcome.elapsed > 0 else 0.0
        total = outcome.ai_active_seconds + outcome.expert_active_seconds + outcome.metadata.get("overhead_seconds", 0.0)
        expert_share = outcome.expert_active_seconds / total if total > 0 else 0.0
        return MetricResult(
            key=self.key,
            value=efficiency,
            label=self.label,
            higher_is_better=self.higher_is_better,
            detail={
                "time_efficiency": efficiency,
                "elapsed": outcome.elapsed,
                "ideal_time": ideal,
                "expert_time_share": expert_share,
            },
        )


class SafetyMetric(PerformanceMetric):
    """Fraction of risk-weighted load handled by the accountable role.

    Reads the responsibility map from meta-knowledge: a critical step handled
    by an unqualified role drags safety down proportionally to its risk.
    """

    key = "safety"
    label = "Safety"
    higher_is_better = True

    def __init__(self, metaknowledge: Optional[OrganizationalMetaknowledge] = None) -> None:
        super().__init__(metaknowledge)
        self._meta = metaknowledge or OrganizationalMetaknowledge()

    def compute(self, outcome: TaskOutcome) -> MetricResult:
        total_risk = outcome.task.total_risk or 1.0
        mishandled_risk = 0.0
        for o in outcome.step_outcomes:
            responsible = self._meta.responsibility_for(o.step.risk)
            ok = (
                responsible == "shared"
                or (responsible == "expert" and o.controller is Role.EXPERT)
                or (responsible == "ai" and o.controller is Role.AI)
            )
            if not ok:
                mishandled_risk += o.step.risk
        safety = max(0.0, 1.0 - mishandled_risk / total_risk)
        return MetricResult(
            key=self.key,
            value=safety,
            label=self.label,
            higher_is_better=self.higher_is_better,
            detail={
                "mishandled_risk": mishandled_risk,
                "total_risk": total_risk,
                "n_failed_steps": sum(1 for o in outcome.step_outcomes if not o.passed),
            },
        )


class MetricSet:
    """An ordered collection of metrics (mediators or performance)."""

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._metrics: list[PerformanceMetric] = []

    def add(self, metric: PerformanceMetric) -> "MetricSet":
        self._metrics.append(metric)
        return self

    def items(self) -> list[PerformanceMetric]:
        return list(self._metrics)

    def __iter__(self):
        return iter(self._metrics)

    @property
    def keys(self) -> list[str]:
        return [m.key for m in self._metrics]
