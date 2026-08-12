"""Shared domain types for Crusaders.

The vocabulary here mirrors the organisational-level theory the platform is
built around:

    Organisation meta-knowledge (moderator)
        -> Human-Machine Collaboration framework (IV: dynamic power handover)
        -> Mediators (fatigue, decision time, handover accuracy, ...)
        -> Performance (quality, efficiency, safety)
        -> SECI feedback (-> updated meta-knowledge)

The role of ``types.py`` is to give framework authors one small, stable set of
objects they can extend without fighting the platform.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional


class Role(str, Enum):
    """Who holds the wheel at a given moment."""

    AI = "ai"
    EXPERT = "expert"

    @property
    def counterpart(self) -> "Role":
        return Role.EXPERT if self is Role.AI else Role.AI


class HandoverDirection(str, Enum):
    """Direction of a power handover event."""

    AI_TO_EXPERT = "ai->expert"
    EXPERT_TO_AI = "expert->ai"


class HandoverTrigger(str, Enum):
    """What caused a handover to happen."""

    POLICY = "policy"                 # a configured policy fired
    EXPERT_CALLBACK = "expert_callback"  # the human pulled the work back
    AI_ESCALATION = "ai_escalation"   # the AI asked for help
    SCHEDULED = "scheduled"           # fixed cadence in the framework
    EXCEPTION = "exception"           # unexpected condition


class HandoverOutcome(str, Enum):
    """Whether a handover event succeeded."""

    SUCCESS = "success"
    FAILED = "failed"
    REDIRECTED = "redirected"


class HandoverState(str, Enum):
    """Global controller state of the framework at any instant."""

    AI_CONTROL = "ai_control"
    EXPERT_CONTROL = "expert_control"
    TRANSFERRING = "transferring"


@dataclass
class StepSpec:
    """A single unit of work in a task. Keep it small and pure data."""

    id: str
    description: str
    complexity: float = 0.5   # 0..1, difficulty of the step
    risk: float = 0.0         # 0..1, severity if the step is mishandled
    requires_expert: bool = False  # hard constraint, cannot be delegated

    def __post_init__(self) -> None:
        self.complexity = _clamp01(self.complexity, "complexity")
        self.risk = _clamp01(self.risk, "risk")


@dataclass
class TaskSpec:
    """A sequence of steps forming one complete job."""

    id: str
    title: str
    steps: list[StepSpec] = field(default_factory=list)
    ideal_time: Optional[float] = None  # best-known duration, for efficiency

    def add_step(self, spec: StepSpec) -> "TaskSpec":
        self.steps.append(spec)
        return self

    @property
    def total_risk(self) -> float:
        return sum(s.risk for s in self.steps)


@dataclass
class AgentDecision:
    """Output produced by one role (AI or expert) for one step.

    ``latency`` is in seconds. ``confidence`` and ``quality_estimate`` are in
    0..1. A real AI adapter will typically produce these from the model; a
    simulated expert produces them from a competence profile.
    """

    role: Role
    step_id: str
    action: str
    content: Any = None
    confidence: float = 0.5
    quality_estimate: float = 0.5
    latency: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class StepContext:
    """Snapshot handed to policies and roles for one step."""

    task: TaskSpec
    step: StepSpec
    index: int
    state: dict[str, Any] = field(default_factory=dict)
    current_controller: Role = Role.AI
    expert_load: float = 0.0   # fatigue / cognitive load of the human so far
    ai_confidence: float = 0.5

    @property
    def step_id(self) -> str:
        return self.step.id


@dataclass
class SessionSnapshot:
    """Immutable view of mediator state at the end of one step."""

    cognitive_load: float = 0.0
    fatigue: float = 0.0
    expert_steps: int = 0
    ai_steps: int = 0
    ai_active_seconds: float = 0.0
    expert_active_seconds: float = 0.0
    overhead_seconds: float = 0.0


@dataclass
class StepOutcome:
    """Result of processing one step."""

    step: StepSpec
    decision: AgentDecision
    controller: Role
    handovers: list["HandoverEvent"] = field(default_factory=list)
    passed: bool = True
    note: str = ""
    session: Optional["SessionSnapshot"] = None


@dataclass
class HandoverEvent:
    """A single power-handover event. Everything observable happens through
    these events, so tracing + mediator computation can be derived uniformly.
    """

    timestamp: float
    direction: HandoverDirection
    trigger: HandoverTrigger
    step_id: str
    reason: str
    outcome: HandoverOutcome = HandoverOutcome.SUCCESS
    context_snapshot: Mapping[str, Any] = field(default_factory=dict)
    duration: float = 0.0  # handover overhead in seconds
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<HandoverEvent {self.timestamp:.2f}s {self.direction.value} "
            f"trigger={self.trigger.value} outcome={self.outcome.value} "
            f"step={self.step_id}>"
        )


@dataclass
class TaskOutcome:
    """Final result of running a whole task through a framework."""

    task: TaskSpec
    step_outcomes: list[StepOutcome] = field(default_factory=list)
    events: list[HandoverEvent] = field(default_factory=list)
    elapsed: float = 0.0
    expert_active_seconds: float = 0.0
    ai_active_seconds: float = 0.0
    successful: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def n_steps(self) -> int:
        return len(self.step_outcomes)

    @property
    def passed_steps(self) -> int:
        return sum(1 for s in self.step_outcomes if s.passed)

    @property
    def n_handovers(self) -> int:
        return len(self.events)

    def last_event(self) -> Optional[HandoverEvent]:
        return self.events[-1] if self.events else None


def _clamp01(value: float, name: str) -> float:
    if value < 0.0 or value > 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")
    return float(value)
