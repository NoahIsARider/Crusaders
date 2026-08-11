"""Handover policies.

A *policy* is a pure function that decides, for a single step, whether control
should move. Frameworks compose policies; the moderation effect of
meta-knowledge appears here, because policies read ``OrganizationalMetaknowledge``
to set their thresholds.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from .core.types import HandoverTrigger, Role, StepContext
from .metaknowledge import OrganizationalMetaknowledge


@dataclass
class PolicyDecision:
    """A policy's recommendation."""

    hand_over: bool
    direction: Optional[Role]  # the role that should take control, or None
    trigger: HandoverTrigger = HandoverTrigger.POLICY
    reason: str = ""


@dataclass
class SessionState:
    """Mutable runtime state shared by policies, roles and observers.

    This is where mediator state (fatigue, cognitive load, decision-time
    bookkeeping) lives during a run, so that *load-aware policies* can see it.
    """

    step_index: int = 0
    current_controller: Role = Role.AI
    expert_active_seconds: float = 0.0
    ai_active_seconds: float = 0.0
    overhead_seconds: float = 0.0
    consecutive_ai_steps: int = 0
    consecutive_expert_steps: int = 0

    # mediator accumulators
    cognitive_load: float = 0.0     # 0..1 running estimate of human load
    fatigue: float = 0.0            # 0..1
    expert_steps: int = 0
    ai_steps: int = 0


class HandoverPolicy(ABC):
    """Base class for every handover policy."""

    name: str = "policy"

    def __init__(self) -> None:
        self._metaknowledge: Optional[OrganizationalMetaknowledge] = None

    def bind(self, metaknowledge: OrganizationalMetaknowledge) -> None:
        """Called by the framework so the policy can read the moderator."""
        self._metaknowledge = metaknowledge

    @property
    def meta(self) -> OrganizationalMetaknowledge:
        if self._metaknowledge is None:
            raise RuntimeError(f"policy {self.name!r} is not bound to meta-knowledge")
        return self._metaknowledge

    @abstractmethod
    def decide(self, step: StepContext, session: SessionState) -> PolicyDecision:
        """Return a recommendation for the given step."""


class RiskGatePolicy(HandoverPolicy):
    """Hand work to the expert when step risk crosses a threshold.

    The threshold is *moderated* by meta-knowledge: organisations that trust a
    wide AI boundary raise the gate (the AI keeps more work), organisations with
    a narrow boundary lower it (they delegate to the expert sooner).
    """

    name = "risk_gate"

    def __init__(self, base_threshold: float = 0.5) -> None:
        super().__init__()
        self.base_threshold = _clamp(base_threshold)

    def decide(self, step: StepContext, session: SessionState) -> PolicyDecision:
        risk = step.step.risk
        boundary = self.meta.max_ai_complexity(default=1.0)
        threshold = self.base_threshold * boundary
        if step.step.requires_expert:
            return PolicyDecision(True, Role.EXPERT, reason="step requires expert")
        if risk > threshold:
            return PolicyDecision(
                True,
                Role.EXPERT,
                reason=f"risk {risk:.2f} > gate {threshold:.2f}",
            )
        return PolicyDecision(False, None, reason="risk within gate")


class LoadAwarePolicy(HandoverPolicy):
    """Give the human a breather by moving work to the AI when fatigue climbs.

    Uses the expert session limit from meta-knowledge as the reference point.
    """

    name = "load_aware"

    def __init__(self, fatigue_ceiling: float = 0.8) -> None:
        super().__init__()
        self.fatigue_ceiling = _clamp(fatigue_ceiling)

    def decide(self, step: StepContext, session: SessionState) -> PolicyDecision:
        limit = self.meta.expert_session_limit(default=6)
        if session.fatigue >= self.fatigue_ceiling and session.current_controller is Role.EXPERT:
            return PolicyDecision(
                True,
                Role.AI,
                reason=f"fatigue {session.fatigue:.2f} >= ceiling; session limit {limit}",
            )
        if session.expert_steps >= limit:
            return PolicyDecision(
                True, Role.AI, reason=f"expert session limit {limit} reached"
            )
        return PolicyDecision(False, None, reason="load within bounds")


class ConfidencePolicy(HandoverPolicy):
    """Let the expert step in when the AI's confidence drops too low."""

    name = "confidence"

    def __init__(self, floor: float = 0.4) -> None:
        super().__init__()
        self.floor = _clamp(floor)

    def decide(self, step: StepContext, session: SessionState) -> PolicyDecision:
        if session.current_controller is Role.AI and step.ai_confidence < self.floor:
            return PolicyDecision(
                True,
                Role.EXPERT,
                reason=f"ai confidence {step.ai_confidence:.2f} < {self.floor}",
            )
        return PolicyDecision(False, None, reason="confidence acceptable")


class AlwaysAI(HandoverPolicy):
    """Trivial policy: AI always keeps control (baseline / ablation)."""

    name = "always_ai"

    def decide(self, step: StepContext, session: SessionState) -> PolicyDecision:
        return PolicyDecision(True, Role.AI, reason="fixed preference")


class AlwaysExpert(HandoverPolicy):
    """Trivial policy: expert always keeps control (baseline / ablation)."""

    name = "always_expert"

    def decide(self, step: StepContext, session: SessionState) -> PolicyDecision:
        return PolicyDecision(True, Role.EXPERT, reason="fixed preference")


class CompositePolicy(HandoverPolicy):
    """Vote-based combiner.

    Each sub-policy votes for a role; if enough policies (>= ``majority`` of
    all sub-policies) want the *other* role to take over, the handover happens.
    Useful for building real-world frameworks out of simple building blocks.
    """

    name = "composite"

    def __init__(self, policies: list[HandoverPolicy], majority: float = 0.5) -> None:
        super().__init__()
        if not policies:
            raise ValueError("composite policy needs at least one sub-policy")
        self.policies = policies
        self.majority = majority

    def bind(self, metaknowledge: OrganizationalMetaknowledge) -> None:
        super().bind(metaknowledge)
        for p in self.policies:
            p.bind(metaknowledge)

    def decide(self, step: StepContext, session: SessionState) -> PolicyDecision:
        expert_votes = 0
        ai_votes = 0
        for policy in self.policies:
            decision = policy.decide(step, session)
            if decision.hand_over and decision.direction is Role.EXPERT:
                expert_votes += 1
            elif decision.hand_over and decision.direction is Role.AI:
                ai_votes += 1
        total = len(self.policies)
        threshold = self.majority * total
        if session.current_controller is Role.AI and expert_votes >= threshold:
            return PolicyDecision(True, Role.EXPERT, reason=f"{expert_votes}/{total} vote expert")
        if session.current_controller is Role.EXPERT and ai_votes >= threshold:
            return PolicyDecision(True, Role.AI, reason=f"{ai_votes}/{total} vote ai")
        return PolicyDecision(False, None, reason="no majority to hand over")


def _clamp(value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"threshold must be in [0, 1], got {value}")
    return float(value)
