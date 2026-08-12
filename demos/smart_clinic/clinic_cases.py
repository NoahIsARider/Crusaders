"""Smart community clinic - domain knowledge.

This module models the *clinic* for the demo: the organisational
meta-knowledge (how much the AI is trusted, who owns risk) and a realistic
patient roster. Each patient is turned into a :class:`TaskSpec` whose steps
mirror a real consultation:

    1. symptoms - structured intake of the chief complaint
    2. history  - past history / medication / allergies
    3. vitals   - vital sign assessment
    4. diagnosis - differential diagnosis (the handover battleground)
    5. plan     - treatment plan / prescription / referral

The *clinically* interesting knobs are on the diagnosis step:

* ``risk`` is the symptom acuity / severity,
* ``complexity`` is the presentation ambiguity (how confusing the picture is),
* ``requires_expert`` marks red flags and vulnerable populations (children,
  the elderly, unstable patients) where the doctor MUST take over no matter
  how good the AI looks.

Design it this way and the framework in ``clinic_framework.py`` can make its
"AI diagnoses vs doctor takes over" decision purely from the risk bands in the
meta-knowledge plus the step profile - no magic, no hard-coded patient names.
"""

from __future__ import annotations

from dataclasses import dataclass

from crusaders import OrganizationalMetaknowledge, RiskResponsibility, StepSpec, TaskSpec

DOMAIN = "smart_clinic"

# Risk bands: responsibility up to 0.3 is AI-owned, up to 0.6 is shared
# (AI recommends / doctor approves), anything above belongs to the doctor.
RISK_BANDS = [
    RiskResponsibility(0.3, "ai"),
    RiskResponsibility(0.6, "shared"),
    RiskResponsibility(1.0, "expert"),
]

# The clinic's trust in its AI: it may autonomously handle consultations up
# to this complexity. Beyond that, the picture is considered too ambiguous.
AI_MAX_COMPLEXITY = 0.6


def default_metaknowledge() -> OrganizationalMetaknowledge:
    """A modern community clinic that trusts AI on routine care but keeps
    a clinician accountable for anything risky."""
    return OrganizationalMetaknowledge(
        ai_boundary={
            "max_complexity": AI_MAX_COMPLEXITY,
            "allowed_domains": ["symptom_intake", "common_illness", "health_advice"],
        },
        expert_capability={
            "max_steps_per_session": 6,
            "strengths": [
                "red_flags",
                "chronic_disease",
                "pediatrics",
                "geriatrics",
                "mental_health",
                "polypharmacy",
            ],
        },
        risk_responsibility=RISK_BANDS,
        handover_timing={"prefer_early": 0.3, "handover_overhead_budget": 1.0},
    )


@dataclass(frozen=True)
class Patient:
    """A patient profile condensed into the knobs a handover framework reads.

    Fields
    ------
    id:
        Stable identifier, also used as the task id.
    title:
        Human-readable presentation (what the patient walks in with).
    group:
        Adult / child / elderly / adolescent. Drives the vulnerability rule.
    acuity:
        Risk of the diagnosis step (0..1). How bad if the diagnosis is wrong.
    ambiguity:
        Complexity of the diagnosis step (0..1). How confusing the picture is.
    vulnerable:
        Red flag - the doctor must take over the diagnosis regardless of AI
        performance (children, frail elderly, unstable presentations).
    plan_risk:
        Risk of the treatment / prescription step (0..1).
    rx_needs_doctor:
        Whether writing the plan requires a clinician (prescription change,
        mental-health plan, dose adjustment).
    """

    id: str
    title: str
    group: str
    acuity: float
    ambiguity: float
    vulnerable: bool
    plan_risk: float
    rx_needs_doctor: bool


PATIENTS: list[Patient] = [
    Patient("p-01", "普通感冒（成人）", "adult", 0.15, 0.20, False, 0.20, False),
    Patient("p-02", "过敏性鼻炎", "adult", 0.20, 0.30, False, 0.25, False),
    Patient("p-03", "季节性流感", "adult", 0.35, 0.40, False, 0.30, False),
    Patient("p-04", "疑似尿路感染", "adult", 0.45, 0.50, False, 0.50, True),
    Patient("p-05", "不明原因乏力", "adult", 0.50, 0.75, False, 0.45, True),
    Patient("p-06", "儿童持续发热3天", "child", 0.55, 0.50, True, 0.60, True),
    Patient("p-07", "老年头晕伴跌倒风险", "elderly", 0.75, 0.60, True, 0.70, True),
    Patient("p-08", "胸痛伴气促", "adult", 0.90, 0.70, True, 0.85, True),
    Patient("p-09", "2型糖尿病随访（调整胰岛素）", "adult", 0.60, 0.50, False, 0.55, True),
    Patient("p-10", "青少年焦虑失眠", "adolescent", 0.35, 0.45, False, 0.50, True),
]


def _consultation(patient: Patient) -> TaskSpec:
    return (
        TaskSpec(patient.id, patient.title)
        .add_step(
            StepSpec(
                f"{patient.id}-symptoms",
                "采集主诉与症状细节",
                complexity=0.2,
                risk=0.1,
            )
        )
        .add_step(
            StepSpec(
                f"{patient.id}-history",
                "问诊既往史 / 用药史 / 过敏史",
                complexity=0.35,
                risk=0.2,
            )
        )
        .add_step(
            StepSpec(
                f"{patient.id}-vitals",
                "评估生命体征（体温 / 血压 / 心率）",
                complexity=0.4,
                risk=0.3,
            )
        )
        .add_step(
            StepSpec(
                f"{patient.id}-diagnosis",
                "形成鉴别诊断与初步诊断",
                complexity=patient.ambiguity,
                risk=patient.acuity,
                requires_expert=patient.vulnerable,
            )
        )
        .add_step(
            StepSpec(
                f"{patient.id}-plan",
                "制定治疗方案与处方",
                complexity=0.5,
                risk=patient.plan_risk,
                requires_expert=patient.rx_needs_doctor,
            )
        )
    )


def _comprehensive_assessment() -> TaskSpec:
    """An extra-long consult: a new-patient comprehensive geriatric
    assessment. Seven consecutive doctor-owned screening steps exhaust the
    clinician's session budget, which is exactly what the load-aware handover
    rule in ``clinic_framework.py`` is designed to react to."""
    return (
        TaskSpec("p-11", "老年综合评估（新患者建档）")
        .add_step(StepSpec("p-11-symptoms", "采集主诉与症状", complexity=0.2, risk=0.1))
        .add_step(StepSpec("p-11-history", "问诊既往史 / 用药史", complexity=0.35, risk=0.2))
        .add_step(StepSpec("p-11-vitals", "评估生命体征", complexity=0.4, risk=0.3))
        .add_step(StepSpec("p-11-risk", "慢性病风险评估", complexity=0.6, risk=0.70, requires_expert=True))
        .add_step(StepSpec("p-11-meds", "多重用药核对", complexity=0.6, risk=0.65, requires_expert=True))
        .add_step(StepSpec("p-11-fall", "跌倒风险筛查", complexity=0.55, risk=0.70, requires_expert=True))
        .add_step(StepSpec("p-11-mental", "心理健康初筛", complexity=0.5, risk=0.60, requires_expert=True))
        .add_step(StepSpec("p-11-mobility", "活动能力评估", complexity=0.5, risk=0.60, requires_expert=True))
        .add_step(StepSpec("p-11-nutrition", "营养状态评估", complexity=0.5, risk=0.60, requires_expert=True))
        .add_step(StepSpec("p-11-home", "居家环境安全评估", complexity=0.5, risk=0.65, requires_expert=True))
        .add_step(StepSpec("p-11-record", "健康档案录入与随访提醒", complexity=0.3, risk=0.2))
        .add_step(StepSpec("p-11-plan", "制定整体健康管理方案", complexity=0.6, risk=0.60, requires_expert=True))
    )


def tasks() -> list[TaskSpec]:
    """A full clinic morning: the standard roster plus one comprehensive
    new-patient assessment."""
    return [_consultation(p) for p in PATIENTS] + [_comprehensive_assessment()]
