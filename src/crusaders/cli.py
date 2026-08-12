"""Command-line entry point: run a quick demo end-to-end.

    crusaders-demo

Runs a small built-in scenario through the built-in adaptive framework,
prints an evaluation report and a sample of the SECI feedback, and writes the
JSON report to ``crusaders_demo_report.json`` in the current directory.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    from .runner import SimulationRunner
    from .seci import SECIEngine
    from .framework import HMCFramework
    from .policies import CompositePolicy, ConfidencePolicy, LoadAwarePolicy, RiskGatePolicy
    from .scenarios import healthcare_triage as triage

    print("Crusaders demo")
    print("=" * 40)
    print()

    framework = HMCFramework(
        name="triage-adaptive",
        metaknowledge=triage.default_metaknowledge(),
        policies=[
            RiskGatePolicy(base_threshold=0.45),
            LoadAwarePolicy(fatigue_ceiling=0.75),
            ConfidencePolicy(floor=0.35),
        ],
    )
    runner = SimulationRunner(framework, seed=7)
    report = runner.evaluate_tasks(triage.tasks())

    print(report.to_markdown())
    print()
    print("SECI feedback")
    print("-" * 40)
    engine = SECIEngine(triage.default_metaknowledge())
    update = engine.run(report)
    for lesson in update.lessons:
        print(f"[{lesson.stage}] {lesson.content}")
    print(f"patch: {update.patch}")
    print(f"recommendations: {update.recommendations}")

    report.to_json("crusaders_demo_report.json")
    print()
    print("Report written to crusaders_demo_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
