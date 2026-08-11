"""Loan underwriting.

Philosophy: *confidence-driven delegation*. The AI does the routine scoring
and document extraction; the underwriter owns edge cases and anything the AI
flags as uncertain. Risk responsibility is mostly shared (AI recommends,
human approves), so the framework leans on ``ConfidencePolicy``.

The reference framework composes the built-in policies to show how easy
framework construction is without writing a single subclass.
"""

from __future__ import annotations

from ..core.types import StepSpec, TaskSpec
from ..framework import HMCFramework
from ..metaknowledge import OrganizationalMetaknowledge, RiskResponsibility
from ..policies import CompositePolicy, ConfidencePolicy, LoadAwarePolicy, RiskGatePolicy

DOMAIN = "financial_underwriting"


def default_metaknowledge() -> OrganizationalMetaknowledge:
    """An organisation that trusts AI on routine work but requires human sign-off."""
    return OrganizationalMetaknowledge(
        ai_boundary={
            "max_complexity": 0.65,
            "allowed_domains": ["ocr", "credit_scoring", "document_extraction"],
        },
        expert_capability={
            "max_steps_per_session": 8,
            "strengths": ["judgement", "policy_exceptions", "fraud_analysis"],
        },
        risk_responsibility=[
            RiskResponsibility(0.4, "ai"),
            RiskResponsibility(1.0, "shared"),
        ],
        handover_timing={"prefer_early": 0.5, "handover_overhead_budget": 1.5},
    )


def tasks() -> list[TaskSpec]:
    def _file(task_id: str, title: str, complexity: float, risk: float) -> TaskSpec:
        return (
            TaskSpec(task_id, title)
            .add_step(StepSpec(f"{task_id}-extract", "Extract applicant data from documents", complexity=0.35, risk=0.2))
            .add_step(StepSpec(f"{task_id}-score", "Run credit scoring model", complexity=0.3, risk=0.25))
            .add_step(StepSpec(f"{task_id}-verify", "Verify income and employment", complexity=0.55, risk=risk))
            .add_step(StepSpec(f"{task_id}-approve", "Decision memo and risk rating", complexity=complexity, risk=0.7))
        )

    return [
        _file("uw-101", "Prime auto loan", complexity=0.45, risk=0.3),
        _file("uw-102", "Self-employed income review", complexity=0.8, risk=0.7),
        _file("uw-103", "Past-default re-application", complexity=0.7, risk=0.75),
    ]


def framework() -> HMCFramework:
    """Reference framework built purely by composing built-in policies."""
    return HMCFramework(
        name="underwriting-composite",
        metaknowledge=default_metaknowledge(),
        policies=[
            CompositePolicy(
                [
                    RiskGatePolicy(base_threshold=0.55),
                    ConfidencePolicy(floor=0.4),
                    LoadAwarePolicy(fatigue_ceiling=0.8),
                ]
            )
        ],
    )
