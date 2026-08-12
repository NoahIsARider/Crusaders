"""Code review.

Philosophy: *efficiency-driven, load-aware*. The AI does the mechanical pass
over every file; a senior engineer only joins for the files the policies flag
(criticality / complexity) and gets the work routed back to the AI when their
load gets high. This is the most "productivity tool" flavoured of the three
reference scenarios.

The reference framework shows the load-aware handover in action and how
organisational meta-knowledge tunes the expert's session budget.
"""

from __future__ import annotations

from ..core.types import StepSpec, TaskSpec
from ..framework import HMCFramework
from ..metaknowledge import OrganizationalMetaknowledge, RiskResponsibility
from ..policies import ConfidencePolicy, LoadAwarePolicy, RiskGatePolicy

DOMAIN = "code_review"


def default_metaknowledge() -> OrganizationalMetaknowledge:
    """A team that lets AI do heavy lifting but protects engineer attention."""
    return OrganizationalMetaknowledge(
        ai_boundary={
            "max_complexity": 0.7,
            "allowed_domains": ["linting", "security_patterns", "test_gap_analysis"],
        },
        expert_capability={
            "max_steps_per_session": 4,
            "strengths": ["architecture", "design_negotiation", "api_compat"],
        },
        risk_responsibility=[
            RiskResponsibility(0.5, "ai"),
            RiskResponsibility(1.0, "expert"),
        ],
        handover_timing={"prefer_early": 0.4, "handover_overhead_budget": 1.0},
    )


def tasks() -> list[TaskSpec]:
    def _pr(task_id: str, title: str, n_hard_files: int) -> TaskSpec:
        task = TaskSpec(task_id, title)
        for i in range(4):
            hard = i < n_hard_files
            task.add_step(
                StepSpec(
                    f"{task_id}-f{i}",
                    "Review " + ("critical module" if hard else "supporting file"),
                    complexity=0.75 if hard else 0.35,
                    risk=0.85 if hard else 0.25,
                    requires_expert=hard,
                )
            )
        return task

    return [
        _pr("pr-501", "Auth service rewrite", n_hard_files=3),
        _pr("pr-502", "Rename and refactor utilities", n_hard_files=0),
        _pr("pr-503", "Payment webhook changes", n_hard_files=2),
    ]


def framework() -> HMCFramework:
    """Reference framework: AI-first, engineer steps in for critical files."""
    return HMCFramework(
        name="review-ai-first",
        metaknowledge=default_metaknowledge(),
        policies=[
            RiskGatePolicy(base_threshold=0.6),
            ConfidencePolicy(floor=0.35),
            LoadAwarePolicy(fatigue_ceiling=0.7),
        ],
    )
