"""Mediators.

The theoretical model says dynamic power handover does not change performance
directly: it first changes *process variables* (fatigue / cognitive load,
decision time, handover accuracy) which then cascade into quality, efficiency
and safety. These are the process variables.

``Mediator`` is an open protocol -- add your own (trust, situational
awareness, ...) by subclassing :class:`MediatorBase` and registering it with a
:class:`MediatorRegistry`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from ..core.types import Role, SessionSnapshot, StepOutcome, TaskOutcome
from ..metaknowledge import OrganizationalMetaknowledge


@dataclass
class MetricResult:
    """Output of one mediator or performance metric."""

    key: str
    value: float
    label: str
    higher_is_better: bool
    detail: dict[str, Any] = field(default_factory=dict)
    series: list[float] = field(default_factory=list)

    @property
    def render(self) -> str:
        return f"{self.label}: {self.value:.3f}"


class MediatorBase(ABC):
    """Compute a process variable from a task outcome."""

    key: str = "mediator"
    label: str = "Mediator"
    higher_is_better: bool = True

    def __init__(self, metaknowledge: Optional[OrganizationalMetaknowledge] = None) -> None:
        self.metaknowledge = metaknowledge

    @abstractmethod
    def compute(self, outcome: TaskOutcome) -> MetricResult: ...

    def _snapshots(self, outcome: TaskOutcome) -> list[SessionSnapshot]:
        return [s.session for s in outcome.step_outcomes if s.session is not None]


class FatigueMediator(MediatorBase):
    """Mean sustained human fatigue across the task (lower is better)."""

    key = "fatigue"
    label = "Mean human fatigue"
    higher_is_better = False

    def compute(self, outcome: TaskOutcome) -> MetricResult:
        series = [s.fatigue for s in self._snapshots(outcome)]
        value = sum(series) / len(series) if series else 0.0
        peak = max(series) if series else 0.0
        return MetricResult(
            key=self.key,
            value=value,
            label=self.label,
            higher_is_better=self.higher_is_better,
            series=series,
            detail={"peak": peak, "expert_steps": sum(1 for o in outcome.step_outcomes if o.controller is Role.EXPERT)},
        )


class CognitiveLoadMediator(MediatorBase):
    """Mean cognitive load imposed on the human (lower is better)."""

    key = "cognitive_load"
    label = "Mean cognitive load"
    higher_is_better = False

    def compute(self, outcome: TaskOutcome) -> MetricResult:
        series = [s.cognitive_load for s in self._snapshots(outcome)]
        value = sum(series) / len(series) if series else 0.0
        return MetricResult(
            key=self.key,
            value=value,
            label=self.label,
            higher_is_better=self.higher_is_better,
            series=series,
            detail={"peak": max(series) if series else 0.0},
        )


class DecisionTimeMediator(MediatorBase):
    """Time spent in productive decisions, excluding handover overhead.

    Shown both as a mean per step and as a total.
    """

    key = "decision_time"
    label = "Mean decision time per step"
    higher_is_better = False

    def compute(self, outcome: TaskOutcome) -> MetricResult:
        series = [o.decision.latency for o in outcome.step_outcomes]
        value = sum(series) / len(series) if series else 0.0
        return MetricResult(
            key=self.key,
            value=value,
            label=self.label,
            higher_is_better=self.higher_is_better,
            series=series,
            detail={
                "total_decision_time": outcome.ai_active_seconds + outcome.expert_active_seconds,
                "handover_overhead": outcome.metadata.get("overhead_seconds", 0.0),
                "n_handovers": outcome.n_handovers,
            },
        )


class HandoverAccuracyMediator(MediatorBase):
    """How well handovers matched the organisation's responsibility map.

    A step is *accurately handled* when the controller equals the role the
    meta-knowledge assigns to the step's risk band (a "shared" band counts
    either role). Churn (AI->Expert->AI zigzags) penalises the score.
    """

    key = "handover_accuracy"
    label = "Handover accuracy"
    higher_is_better = True

    def __init__(self, metaknowledge: Optional[OrganizationalMetaknowledge] = None) -> None:
        super().__init__(metaknowledge)
        self._meta = metaknowledge or OrganizationalMetaknowledge()

    def compute(self, outcome: TaskOutcome) -> MetricResult:
        per_step: list[float] = []
        for o in outcome.step_outcomes:
            responsible = self._meta.responsibility_for(o.step.risk)
            ok = (
                responsible == "shared"
                or (responsible == "expert" and o.controller is Role.EXPERT)
                or (responsible == "ai" and o.controller is Role.AI)
            )
            per_step.append(1.0 if ok else 0.0)
        accuracy = sum(per_step) / len(per_step) if per_step else 0.0

        churn = 0
        prev = None
        for e in outcome.events:
            if prev is not None and e.direction is not prev:
                churn += 1
            prev = e.direction
        churn_rate = churn / outcome.n_handovers if outcome.n_handovers else 0.0
        value = max(0.0, accuracy - churn_rate * 0.5)
        return MetricResult(
            key=self.key,
            value=value,
            label=self.label,
            higher_is_better=self.higher_is_better,
            series=per_step,
            detail={
                "accuracy": accuracy,
                "churn": churn,
                "n_handovers": outcome.n_handovers,
            },
        )


class MediatorRegistry:
    """Collect mediators into one list with stable keys."""

    def __init__(self, mediators: Optional[list[MediatorBase]] = None) -> None:
        self._mediators: list[MediatorBase] = []
        for m in mediators or []:
            self.add(m)

    def add(self, mediator: MediatorBase) -> "MediatorRegistry":
        self._mediators.append(mediator)
        return self

    def get(self, key: str) -> Optional[MediatorBase]:
        for m in self._mediators:
            if m.key == key:
                return m
        return None

    def items(self) -> list[MediatorBase]:
        return list(self._mediators)

    def __iter__(self):
        return iter(self._mediators)

    @property
    def keys(self) -> list[str]:
        return [m.key for m in self._mediators]
