"""SECI feedback engine.

Closes the loop: observed performance flows back through Nonaka's
socialisation / externalisation / combination / internalisation cycle and
becomes *updated organisational meta-knowledge*, ready to moderate the next
round of collaboration.

The mapping is intentionally concrete so the loop is testable:

* **Socialisation** -- shared field observations distilled from the runs.
* **Externalisation** -- observations converted into explicit lessons.
* **Combination** -- lessons combined into numeric meta-knowledge patches.
* **Internalisation** -- recommended policy knobs for the next round.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .metaknowledge import OrganizationalMetaknowledge
from .observability import EvaluationReport


@dataclass
class Lesson:
    """A single codified item of knowledge produced by the SECI cycle."""

    stage: str  # socialization | externalization | combination | internalization
    content: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeUpdate:
    """Everything the SECI cycle produces."""

    lessons: list[Lesson] = field(default_factory=list)
    patch: dict[str, Any] = field(default_factory=dict)
    recommendations: dict[str, Any] = field(default_factory=dict)

    def apply(self, metaknowledge: OrganizationalMetaknowledge) -> OrganizationalMetaknowledge:
        """Apply the patch to a copy of the meta-knowledge."""
        updated = metaknowledge.clone()
        if self.patch:
            updated.update_from(self.patch)
        for lesson in self.lessons:
            if lesson.content not in updated.lessons:
                updated.lessons.append(lesson.content)
        return updated


class SECIEngine:
    """Default feedback loop. Override ``rules`` or subclass for your own."""

    def __init__(
        self, metaknowledge: Optional[OrganizationalMetaknowledge] = None, learning_rate: float = 0.2
    ) -> None:
        self.metaknowledge = metaknowledge or OrganizationalMetaknowledge()
        if not 0.0 < learning_rate <= 1.0:
            raise ValueError("learning_rate must be in (0, 1]")
        self.learning_rate = learning_rate

    # -- entry point -----------------------------------------------------------

    def run(self, report: EvaluationReport) -> KnowledgeUpdate:
        aggregate = report.aggregated()
        return KnowledgeUpdate(
            lessons=self.socialize(report) + self.externalize(aggregate),
            patch=self.combine(aggregate),
            recommendations=self.internalize(aggregate),
        )

    # -- stages ----------------------------------------------------------------

    def socialize(self, report: EvaluationReport) -> list[Lesson]:
        """Shared field observations: what actually happened across runs."""
        lessons: list[Lesson] = []
        if not report.runs:
            return lessons
        handovers = [r.outcome.n_handovers for r in report.runs]
        pass_counts = [r.outcome.passed_steps for r in report.runs]
        n_steps = report.runs[0].outcome.n_steps or 1
        lessons.append(
            Lesson(
                "socialization",
                f"Across {report.n_runs} runs the team averaged "
                f"{sum(handovers)/len(handovers):.1f} handovers and "
                f"{sum(pass_counts)/len(pass_counts):.1f}/{n_steps} passed steps.",
                evidence={"n_runs": report.n_runs, "mean_handovers": sum(handovers) / len(handovers)},
            )
        )
        return lessons

    def externalize(self, aggregate: dict[str, float]) -> list[Lesson]:
        """Explicit if-then lessons distilled from measured values."""
        lessons: list[Lesson] = []
        fatigue = aggregate.get("fatigue", 0.5)
        if fatigue >= 0.6:
            lessons.append(
                Lesson(
                    "externalization",
                    "When mean human fatigue reaches "
                    f"{fatigue:.2f}, the framework should offload work to the AI.",
                    evidence={"fatigue": fatigue},
                )
            )
        accuracy = aggregate.get("handover_accuracy", 1.0)
        if accuracy < 0.8:
            lessons.append(
                Lesson(
                    "externalization",
                    "Handover accuracy "
                    f"({accuracy:.2f}) is below target; re-check the risk responsibility map.",
                    evidence={"handover_accuracy": accuracy},
                )
            )
        return lessons

    def combine(self, aggregate: dict[str, float]) -> dict[str, Any]:
        """Merge lessons into numeric meta-knowledge patches."""
        patch: dict[str, Any] = {}
        lr = self.learning_rate

        fatigue = aggregate.get("fatigue", 0.5)
        safety = aggregate.get("safety", 1.0)
        quality = aggregate.get("quality", 0.8)
        accuracy = aggregate.get("handover_accuracy", 1.0)

        # Narrows the AI boundary if fatigue or safety suffers.
        current_max = self.metaknowledge.max_ai_complexity()
        target = current_max
        if fatigue >= 0.6 or safety < 0.85:
            target = max(0.2, current_max - lr * (0.5 + (1.0 - safety)))
        elif quality < 0.7 and fatigue < 0.4:
            # AI underperforming while human has headroom -> shrink AI scope
            target = max(0.2, current_max - lr * 0.3)
        if target != current_max:
            patch["ai_boundary"] = {"max_complexity": round(target, 4)}

        # Human session limit reacts to fatigue and quality.
        limit = self.metaknowledge.expert_session_limit()
        if fatigue >= 0.6:
            patch["expert_capability"] = {"max_steps_per_session": max(1, limit - 1)}
        elif fatigue < 0.3 and quality >= 0.85:
            patch["expert_capability"] = {"max_steps_per_session": limit + 1}

        # Handover cost budget adapts to how costly handovers proved.
        decision_time = aggregate.get("decision_time", 0.0)
        if decision_time > 0 and accuracy < 0.8:
            budget = self.metaknowledge.handover_overhead_budget()
            patch["handover_timing"] = {"handover_overhead_budget": round(min(10.0, budget + lr * 2), 4)}

        return patch

    def internalize(self, aggregate: dict[str, float]) -> dict[str, Any]:
        """Codified policy knobs recommended for the next round."""
        recommendations: dict[str, Any] = {}
        fatigue = aggregate.get("fatigue", 0.5)
        if fatigue >= 0.6:
            recommendations["load_aware.fatigue_ceiling"] = max(0.4, 0.8 - self.learning_rate * 0.5)
        if aggregate.get("handover_accuracy", 1.0) < 0.8:
            recommendations["risk_gate.base_threshold"] = max(0.2, 0.5 - self.learning_rate * 0.3)
        return recommendations
