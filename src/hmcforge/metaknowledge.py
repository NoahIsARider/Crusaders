"""Organisation meta-knowledge.

In the theoretical model, meta-knowledge is the *moderator*: the organisation's
understanding of AI boundaries, expert capability, risk responsibility and
handover timing shapes how any human-machine collaboration framework gets
designed and tuned.

``OrganizationalMetaknowledge`` is deliberately a plain, extensible data
structure. Framework authors read from it inside their policies (that is what
makes the moderation effect concrete) and the SECI engine writes updates back
to it after evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping


def _clamp(value: float, name: str) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value}")
    return float(value)


@dataclass
class RiskResponsibility:
    """Who carries the accountability at each risk band.

    ``threshold`` is the upper risk bound of the band; ``role`` is the role
    that owns responsibility inside the band.
    """

    threshold: float
    role: str = "expert"  # "ai" | "expert" | "shared"

    def __post_init__(self) -> None:
        self.threshold = _clamp(self.threshold, "threshold")
        if self.role not in {"ai", "expert", "shared"}:
            raise ValueError(f"unknown role {self.role!r}")


@dataclass
class OrganizationalMetaknowledge:
    """The moderator of the framework.

    Attributes
    ----------
    ai_boundary:
        A mapping describing what the AI is currently trusted to do, e.g.
        ``{"max_complexity": 0.7, "allowed_domains": ["triage", "search"]}``.
    expert_capability:
        What the human experts are strong at, e.g.
        ``{"max_steps_per_session": 8, "strengths": ["judgement", "ethics"]}``.
    risk_responsibility:
        Ordered bands of risk -> responsible role. Used by risk-aware policies.
    handover_timing:
        Preferences on when handover should occur, e.g.
        ``{"prefer_early": 0.3, "handover_overhead_budget": 5.0}``.
    lessons:
        Codified knowledge produced by the SECI loop. Starts empty.
    """

    ai_boundary: dict[str, Any] = field(default_factory=dict)
    expert_capability: dict[str, Any] = field(default_factory=dict)
    risk_responsibility: list[RiskResponsibility] = field(
        default_factory=lambda: [RiskResponsibility(1.0, "expert")]
    )
    handover_timing: dict[str, Any] = field(default_factory=dict)
    lessons: list[str] = field(default_factory=list)
    _version: int = 0

    # -- convenience accessors -------------------------------------------------

    @property
    def version(self) -> int:
        return self._version

    def responsibility_for(self, risk: float) -> str:
        """Return the responsible role for a given risk level.

        The highest band whose ``threshold >= risk`` wins.
        """
        for band in self.risk_responsibility:
            if risk <= band.threshold:
                return band.role
        return self.risk_responsibility[-1].role

    def max_ai_complexity(self, default: float = 0.7) -> float:
        return float(self.ai_boundary.get("max_complexity", default))

    def expert_session_limit(self, default: int = 6) -> int:
        return int(self.expert_capability.get("max_steps_per_session", default))

    def handover_overhead_budget(self, default: float = 5.0) -> float:
        return float(self.handover_timing.get("handover_overhead_budget", default))

    def clone(self) -> "OrganizationalMetaknowledge":
        """Deep-ish copy so experiments never mutate shared state in place."""
        return replace(
            self,
            ai_boundary=dict(self.ai_boundary),
            expert_capability=dict(self.expert_capability),
            risk_responsibility=[replace(b) for b in self.risk_responsibility],
            handover_timing=dict(self.handover_timing),
            lessons=list(self.lessons),
        )

    def update_from(self, patch: Mapping[str, Any]) -> "OrganizationalMetaknowledge":
        """Apply an in-place update, bumping the version. Returns self."""
        for key, value in patch.items():
            if key == "risk_responsibility":
                self.risk_responsibility = [
                    v if isinstance(v, RiskResponsibility) else RiskResponsibility(**v)
                    for v in value
                ]
            elif key == "lessons":
                self.lessons = list(value)
            elif key in {"ai_boundary", "expert_capability", "handover_timing"}:
                current = getattr(self, key)
                current.update(value)
            else:
                raise KeyError(f"unknown meta-knowledge field: {key}")
        self._version += 1
        return self

    def summary(self) -> dict[str, Any]:
        return {
            "version": self._version,
            "ai_boundary": self.ai_boundary,
            "expert_capability": self.expert_capability,
            "risk_responsibility": [
                {"threshold": b.threshold, "role": b.role}
                for b in self.risk_responsibility
            ],
            "handover_timing": self.handover_timing,
            "n_lessons": len(self.lessons),
        }
