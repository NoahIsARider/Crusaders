"""Smart clinic demo - run it end to end.

    python run_demo.py

The scenario: a community clinic / family-doctor practice wants an AI
front-desk that handles consultations, but the team has to decide *when the AI
diagnoses on its own and when the doctor takes over*. This script:

    1. Walks through individual consultations, showing every handover decision
       and its reason.
    2. Simulates a full clinic morning (11 patients) and scores the framework.
    3. Closes the SECI feedback loop over several rounds and shows how the
       organisation's meta-knowledge evolves.
    4. Compares the clinic framework against simpler baselines
       (AI-only, doctor-only, a generic policy stack).

All reports are written to ``./outputs/`` as Markdown and JSON.

Run with:  python run_demo.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crusaders import (  # noqa: E402
    AlwaysAI,
    AlwaysExpert,
    CognitiveLoadMediator,
    CompositePolicy,
    ConfidencePolicy,
    DecisionTimeMediator,
    FatigueMediator,
    HandoverAccuracyMediator,
    HMCFramework,
    LoadAwarePolicy,
    RiskGatePolicy,
    Role,
    SECIEngine,
    SimulationRunner,
)

import clinic_cases  # noqa: E402
import clinic_framework  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")

DEFAULT_MEDIATORS = [
    FatigueMediator,
    CognitiveLoadMediator,
    DecisionTimeMediator,
    HandoverAccuracyMediator,
]


def _hr(char: str = "-", width: int = 74) -> str:
    return char * width


def make_runner(framework, seed: int = 7) -> SimulationRunner:
    """SimulationRunner with the default mediators plus the clinic's custom
    ``ai_autonomy`` mediator (demonstrates the mediator extension point)."""
    mediators = [
        cls(framework.metaknowledge) for cls in DEFAULT_MEDIATORS
    ] + [clinic_framework.AutonomousDiagnosisMediator(framework.metaknowledge)]
    return SimulationRunner(framework, mediators=mediators, seed=seed)


# --------------------------------------------------------------------------- #
# 1. Single-consultation walkthrough
# --------------------------------------------------------------------------- #

def walkthrough(framework, task) -> None:
    """Run one consultation and print the choreography step by step."""
    outcome = framework.run(task)
    print(f"\nConsultation: {task.title}  ({task.id})")
    print(_hr())
    for o in outcome.step_outcomes:
        for event in o.handovers:
            print(
                f"  HANDOVER  {event.direction.value:<12} "
                f"[{event.trigger.value}] {event.reason}"
            )
        who = "AI" if o.controller is Role.AI else "DOCTOR"
        flag = "PASS" if o.passed else "FAIL"
        print(
            f"  {o.step.id:<22} {who:<6} conf={o.decision.confidence:.2f} "
            f"qual={o.decision.quality_estimate:.2f}  {flag}"
        )
    print(
        f"  -> {outcome.passed_steps}/{outcome.n_steps} steps passed, "
        f"{outcome.n_handovers} handover(s), {outcome.elapsed:.1f}s simulated"
    )


# --------------------------------------------------------------------------- #
# 2. A full clinic morning
# --------------------------------------------------------------------------- #

def _disposition(outcome) -> str:
    """Summarise who carried the consultation."""
    doctor_any = any(o.controller is Role.EXPERT for o in outcome.step_outcomes)
    diagnosis = next(
        (o for o in outcome.step_outcomes if o.step.id.endswith("-diagnosis")),
        None,
    )
    if diagnosis is not None and diagnosis.controller is Role.EXPERT:
        return "doctor-led diagnosis"
    if doctor_any:
        return "AI diagnosis + doctor plan"
    return "AI handles autonomously"


def clinic_day(framework, tasks, seed: int = 7) -> None:
    """Simulate the whole roster and print a per-patient table + report."""
    report = make_runner(framework, seed=seed).evaluate_tasks(tasks)
    print(f"\nClinic morning - {len(tasks)} patients through "
          f"'{framework.name}'")
    print(_hr())
    print(f"{'patient':<9}{'title':<24}{'who handled it':<28}{'handovers':>9}  pass")
    for run in report.runs:
        print(
            f"{run.task_id:<9}{run.outcome.task.title:<24}"
            f"{_disposition(run.outcome):<28}{run.outcome.n_handovers:>9}  "
            f"{run.outcome.passed_steps}/{run.outcome.n_steps}"
        )
    print()
    print(report.to_markdown())
    return report


# --------------------------------------------------------------------------- #
# 3. SECI feedback loop
# --------------------------------------------------------------------------- #

def seci_loop(framework, tasks, rounds: int = 3) -> None:
    """Let the clinic learn: run, measure, patch meta-knowledge, repeat."""
    print(f"\nSECI feedback loop - the clinic learns ({rounds} rounds)")
    print(_hr())
    meta = framework.metaknowledge
    for r in range(1, rounds + 1):
        report = make_runner(framework).evaluate_tasks(tasks)
        update = SECIEngine(meta, learning_rate=0.2).run(report)
        print(f"\nRound {r}:")
        for lesson in update.lessons:
            print(f"  [{lesson.stage:<15}] {lesson.content}")
        if update.patch:
            print(f"  patch       {update.patch}")
        if update.recommendations:
            print(f"  recommend   {update.recommendations}")
        meta = update.apply(meta)
        framework.metaknowledge = meta
    print("\nMeta-knowledge after learning:")
    print(json.dumps(meta.summary(), ensure_ascii=False, indent=2))
    return meta


# --------------------------------------------------------------------------- #
# 4. Policy comparison
# --------------------------------------------------------------------------- #

def comparison(tasks, seed: int = 7) -> None:
    """Compare the clinic framework against simpler baselines."""
    meta = clinic_cases.default_metaknowledge()

    def _baseline(name, policies):
        return HMCFramework(
            name=name,
            metaknowledge=meta,
            policies=policies,
            step_evaluator=clinic_framework.clinic_step_evaluator,
        )

    frameworks = {
        "adaptive (this demo)": clinic_framework.SmartClinicFramework(
            name="smart-clinic-adaptive", metaknowledge=meta
        ),
        "doctor-only": _baseline("doctor-only", [AlwaysExpert()]),
        "ai-only": _baseline("ai-only", [AlwaysAI()]),
        "generic policy stack": _baseline(
            "clinic-policy-stack",
            [
                CompositePolicy(
                    [
                        RiskGatePolicy(base_threshold=0.45),
                        ConfidencePolicy(floor=0.55),
                        LoadAwarePolicy(fatigue_ceiling=0.8),
                    ]
                )
            ],
        ),
    }

    print(f"\nComparison - one clinic morning under 4 frameworks (seed={seed})")
    print(_hr())
    header = f"{'framework':<26}{'quality':>8}{'eff':>7}{'safety':>8}{'fatigue':>9}{'accuracy':>10}{'autonomy':>9}{'time(s)':>9}"
    print(header)
    print("-" * len(header))

    rows = []
    for name, fw in frameworks.items():
        report = make_runner(fw, seed=seed).evaluate_tasks(tasks)
        agg = report.aggregated()
        rows.append((name, report))
        print(
            f"{name:<26}"
            f"{agg['quality']:>8.2f}"
            f"{agg['efficiency']:>7.2f}"
            f"{agg['safety']:>8.2f}"
            f"{agg['fatigue']:>9.2f}"
            f"{agg['handover_accuracy']:>10.2f}"
            f"{agg['ai_autonomy']:>9.2f}"
            f"{agg['decision_time']:>9.2f}"
        )
    return rows


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 74)
    print("Crusaders demo: smart community clinic / family-doctor practice")
    print("Human-machine consultation - when does AI diagnose, when doctor?")
    print("=" * 74)

    meta = clinic_cases.default_metaknowledge()
    framework = clinic_framework.SmartClinicFramework(
        name="smart-clinic-adaptive", metaknowledge=meta
    )
    tasks = clinic_cases.tasks()

    # --- 1. walkthroughs -----------------------------------------------------
    print("\n[1] Consultation walkthroughs")
    for patient_id in ("p-04", "p-05", "p-11"):
        task = next(t for t in tasks if t.id == patient_id)
        walkthrough(framework, task)

    # --- 2. clinic morning ----------------------------------------------------
    print("\n[2] Full clinic morning")
    report = clinic_day(framework, tasks)

    # --- 3. SECI loop ---------------------------------------------------------
    seci_loop(framework, tasks)

    # --- 4. comparison ---------------------------------------------------------
    rows = comparison(tasks)

    # --- write reports ---------------------------------------------------------
    report.to_markdown(os.path.join(OUTPUT_DIR, "clinic_report.md"))
    report.to_json(os.path.join(OUTPUT_DIR, "clinic_report.json"))
    trace_md = _build_comparison_markdown(rows)
    with open(os.path.join(OUTPUT_DIR, "comparison.md"), "w", encoding="utf-8") as fh:
        fh.write(trace_md)

    print("\nReports written to:", OUTPUT_DIR)
    return 0


def _build_comparison_markdown(rows) -> str:
    lines = [
        "# Framework comparison - smart clinic morning",
        "",
        "Same 11-patient roster, same seed, four handover designs.",
        "",
        "| framework | quality | efficiency | safety | fatigue | handover_accuracy | ai_autonomy | decision_time (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, report in rows:
        agg = report.aggregated()
        lines.append(
            f"| {name} | {agg['quality']:.3f} | {agg['efficiency']:.3f} | "
            f"{agg['safety']:.3f} | {agg['fatigue']:.3f} | "
            f"{agg['handover_accuracy']:.3f} | {agg['ai_autonomy']:.3f} | "
            f"{agg['decision_time']:.2f} |"
        )
    lines += [
        "",
        "Read the numbers, then run the demo yourself: `python run_demo.py`.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
