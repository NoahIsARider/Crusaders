"""Emergency-department triage.

Philosophy: *human-in-the-loop safety net*. The AI streams intake data fast,
but anything above a modest risk band is pulled back by a clinician. The
organisational meta-knowledge encodes a conservative AI boundary and explicit
risk responsibility bands.

The reference framework demonstrates dynamic power handover with two handcrafted
rules (override the base policies for a fully custom framework).
"""

from __future__ import annotations

from ..core.types import HandoverTrigger, Role, StepSpec, TaskSpec
from ..framework import HMCFramework, HandoverDecision
from ..metaknowledge import OrganizationalMetaknowledge, RiskResponsibility
from ..policies import SessionState

DOMAIN = "healthcare_triage"


def default_metaknowledge() -> OrganizationalMetaknowledge:
    """A conservative organisation: narrow AI boundary, experts own risk."""
    return OrganizationalMetaknowledge(
        ai_boundary={
            "max_complexity": 0.5,
            "allowed_domains": ["intake", "vital_signs", "scheduling"],
        },
        expert_capability={
            "max_steps_per_session": 5,
            "strengths": ["differential_diagnosis", "triage_escalation"],
        },
        risk_responsibility=[
            RiskResponsibility(0.35, "ai"),
            RiskResponsibility(0.7, "shared"),
            RiskResponsibility(1.0, "expert"),
        ],
        handover_timing={"prefer_early": 0.2, "handover_overhead_budget": 0.8},
    )


def tasks() -> list[TaskSpec]:
    """A small batch of ED intake tasks with escalating acuity."""

    def _intake(task_id: str, title: str, acuity: float) -> TaskSpec:
        return (
            TaskSpec(task_id, title)
            .add_step(StepSpec(f"{task_id}-vitals", "Capture and parse vital signs", complexity=0.25, risk=0.1))
            .add_step(StepSpec(f"{task_id}-history", "Extract chief complaint and history", complexity=0.45, risk=0.3))
            .add_step(StepSpec(f"{task_id}-flags", "Screen for red-flag symptoms", complexity=0.6, risk=0.8, requires_expert=True))
            .add_step(StepSpec(f"{task_id}-plan", "Draft initial triage disposition", complexity=0.5, risk=acuity, requires_expert=True))
        )

    return [
        _intake("ed-001", "Low-acuity outpatient", acuity=0.2),
        _intake("ed-002", "Chest pain workup", acuity=0.9),
        _intake("ed-003", "Post-op fever review", acuity=0.6),
    ]


class SafetyNetTriageFramework(HMCFramework):
    """Reference framework: escalate on red flags, keep clinician in the loop."""

    def decide_handover(self, step, session: SessionState) -> HandoverDecision:
        spec = step.step
        if spec.requires_expert and session.current_controller is Role.AI:
            return HandoverDecision(Role.EXPERT, HandoverTrigger.AI_ESCALATION, "red flag")
        if step.step.risk <= 0.35 and session.current_controller is Role.EXPERT:
            return HandoverDecision(Role.AI, HandoverTrigger.POLICY, "low-risk step")
        return HandoverDecision(session.current_controller, reason="keep current")


def framework() -> HMCFramework:
    """Ready-to-use example framework for this scenario."""
    return SafetyNetTriageFramework(
        name="triage-safety-net",
        metaknowledge=default_metaknowledge(),
    )
