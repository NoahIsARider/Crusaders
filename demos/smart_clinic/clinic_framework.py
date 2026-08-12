"""Smart community clinic - the collaboration framework.

The clinic's core design question:

    "When does the AI diagnose on its own, and when do we hand the
    consultation over to a doctor?"

:class:`SmartClinicFramework` answers it with five ordered rules. Because the
platform's handover logic is one method, the whole policy is readable top to
bottom - and it reads the organisation's meta-knowledge (risk bands, AI
boundary, doctor session budget) rather than hard-coding thresholds.

Rule order matters and encodes a clinical hierarchy:

    1. **Red flags & vulnerable patients** (``requires_expert``) - children,
       frail elderly, unstable presentations. The doctor takes over. Nothing
       else is consulted.
    2. **Diagnosis step - the autonomy gate.** The AI diagnoses when the
       step's risk band is AI-owned, or is shared *and* within the AI
       complexity boundary (an unambiguous picture). Ambiguous or
       expert-band presentations go to the doctor.
    3. **Plan step.** Prescriptions, dose changes and mental-health plans
       always need a clinician; self-care advice for low-risk complaints does
       not.
    4. **Doctor overload.** When the clinician is at their session budget or
       too fatigued, low-risk work is routed back to the AI so the human can
       breathe.
    5. **Everything else** stays with whoever already holds control - we never
       churn control without a reason.
"""

from __future__ import annotations

from crusaders import HMCFramework, HandoverDecision, Role
from crusaders.core.types import HandoverTrigger, TaskOutcome
from crusaders.mediators import MediatorBase, MetricResult
from crusaders.metaknowledge import OrganizationalMetaknowledge
from crusaders.policies import SessionState

# Model competence: the clinic knows its AI's calibration curve. Confidence is
# high for routine presentations and collapses as ambiguity grows.
def _predicted_ai_confidence(complexity: float) -> float:
    return max(0.05, 0.95 - complexity * 0.6)

# Below this predicted confidence the AI's answer is too shaky to own the
# diagnosis (used as a proxy for "ambiguous presentation").
CONFIDENCE_FLOOR = 0.55

# Steps at or below this risk never need the doctor.
LOW_RISK_GATE = 0.3

# Human session budget before we start routing work back to the AI.
SESSION_LIMIT = 6


def clinic_step_evaluator(decision, spec) -> bool:
    """The clinic's bar for an *acceptable* outcome.

    It still grows with step complexity, but more gently than the platform
    default: the framework has already checked the risk band and the AI
    boundary before letting the AI own a step, so a step the framework cleared
    is expected to be handled well by whoever took it. Supply your own
    evaluator to grade against golden diagnoses instead.
    """
    bar = 0.45 + spec.complexity * 0.3
    return decision.quality_estimate >= bar


class SmartClinicFramework(HMCFramework):
    """AI-first consultation with a clinician safety net.

    Subclass the base class and override the single method the platform
    actually cares about: *who should be in control of the next step*.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("step_evaluator", clinic_step_evaluator)
        super().__init__(**kwargs)

    def decide_handover(
        self, step, session: SessionState
    ) -> HandoverDecision:
        spec = step.step
        meta = self.metaknowledge

        # Rule 1: red flags and vulnerable patients are never delegated.
        if spec.requires_expert:
            is_plan = spec.id.endswith("-plan")
            if session.current_controller is Role.AI:
                return HandoverDecision(
                    Role.EXPERT,
                    trigger=HandoverTrigger.AI_ESCALATION,
                    reason=(
                        "plan / treatment needs doctor"
                        if is_plan
                        else "red flag / vulnerable patient -> doctor"
                    ),
                )
            return HandoverDecision(
                Role.EXPERT,
                reason=(
                    "doctor stays for plan"
                    if is_plan
                    else "critical step stays with doctor"
                ),
            )

        # Rule 2: the diagnosis autonomy gate.
        if spec.id.endswith("-diagnosis"):
            return self._diagnosis_gate(step, session)

        # Rule 3: plan / prescription.
        if spec.id.endswith("-plan"):
            if spec.risk > LOW_RISK_GATE:
                if session.current_controller is Role.AI:
                    return HandoverDecision(
                        Role.EXPERT,
                        trigger=HandoverTrigger.POLICY,
                        reason="prescription / treatment needs doctor",
                    )
                return HandoverDecision(
                    Role.EXPERT, reason="doctor signs the plan"
                )
            if session.current_controller is Role.EXPERT:
                return HandoverDecision(
                    Role.AI,
                    trigger=HandoverTrigger.POLICY,
                    reason="low-risk self-care plan -> AI",
                )
            return HandoverDecision(Role.AI, reason="AI drafts self-care plan")

        # Rule 4: doctor overload - low-risk work goes back to the AI.
        limit = meta.expert_session_limit(default=SESSION_LIMIT)
        if (
            session.current_controller is Role.EXPERT
            and spec.risk <= LOW_RISK_GATE
        ):
            if session.expert_steps >= limit or session.fatigue >= 0.8:
                return HandoverDecision(
                    Role.AI,
                    trigger=HandoverTrigger.POLICY,
                    reason=(
                        f"doctor at session budget ({session.expert_steps}/{limit}) "
                        "or fatigued; low-risk step -> AI"
                    ),
                )
            return HandoverDecision(
                Role.AI,
                trigger=HandoverTrigger.POLICY,
                reason="low-risk step -> AI",
            )

        # Rule 5: no reason to churn control.
        return HandoverDecision(
            session.current_controller, reason="keep current controller"
        )

    def _diagnosis_gate(
        self, step, session: SessionState
    ) -> HandoverDecision:
        """Decide who owns the diagnosis for this patient presentation."""
        spec = step.step
        meta = self.metaknowledge
        boundary = meta.max_ai_complexity(default=0.6)
        responsible = meta.responsibility_for(spec.risk)

        in_boundary = spec.complexity <= boundary
        confident = (
            _predicted_ai_confidence(spec.complexity) >= CONFIDENCE_FLOOR
        )

        if responsible == "ai":
            # Routine, low-acuity complaints: the AI owns them outright.
            if session.current_controller is Role.EXPERT:
                return HandoverDecision(
                    Role.AI,
                    trigger=HandoverTrigger.POLICY,
                    reason="low-acuity diagnosis within AI ownership -> AI",
                )
            return HandoverDecision(
                Role.AI, reason="AI owns low-acuity diagnosis"
            )

        if responsible == "shared":
            # Borderline acuity: AI diagnoses when the picture is unambiguous
            # and inside the AI boundary; ambiguous presentations escalate.
            if in_boundary and confident:
                return HandoverDecision(
                    session.current_controller,
                    reason="AI recommends, picture unambiguous",
                )
            if session.current_controller is Role.AI:
                return HandoverDecision(
                    Role.EXPERT,
                    trigger=HandoverTrigger.AI_ESCALATION,
                    reason="ambiguous presentation -> doctor",
                )
            return HandoverDecision(
                Role.EXPERT, reason="doctor owns ambiguous diagnosis"
            )

        # responsible == "expert": high-acuity presentations belong to the doctor.
        if session.current_controller is Role.AI:
            return HandoverDecision(
                Role.EXPERT,
                trigger=HandoverTrigger.POLICY,
                reason="expert-risk diagnosis -> doctor",
            )
        return HandoverDecision(
            Role.EXPERT, reason="doctor owns high-acuity diagnosis"
        )


class AutonomousDiagnosisMediator(MediatorBase):
    """Custom mediator: what fraction of the consultation did the AI carry?

    This is the number a clinic actually watches day to day - how much of the
    caseload resolved without a clinician. It demonstrates the mediator
    extension point: subclass :class:`MediatorBase`, implement ``compute``,
    pass the instance to :class:`~crusaders.SimulationRunner`.
    """

    key = "ai_autonomy"
    label = "AI autonomy (share of steps)"
    higher_is_better = True

    def __init__(
        self, metaknowledge: OrganizationalMetaknowledge | None = None
    ) -> None:
        super().__init__(metaknowledge)

    def compute(self, outcome: TaskOutcome) -> MetricResult:
        n = outcome.n_steps or 1
        ai_steps = sum(
            1 for o in outcome.step_outcomes if o.controller is Role.AI
        )
        return MetricResult(
            key=self.key,
            value=ai_steps / n,
            label=self.label,
            higher_is_better=self.higher_is_better,
            detail={"ai_steps": ai_steps, "doctor_steps": n - ai_steps},
        )
