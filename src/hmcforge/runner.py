"""Simulation runner.

Runs one framework against a set of tasks (or the same task many times),
evaluates every run with the configured mediators and performance metrics, and
aggregates everything into an :class:`~hmcforge.observability.EvaluationReport`.
"""

from __future__ import annotations

import random
from typing import Optional, Sequence

from .adapters import AIModel, Expert
from .core.types import TaskSpec
from .framework import HMCFramework
from .mediators import MediatorBase, MediatorRegistry, MetricResult
from .observability import EvaluationReport, RunResult, TraceRecorder
from .performance import MetricSet, PerformanceMetric


class SimulationRunner:
    """Orchestrates repeatable evaluations.

    Parameters
    ----------
    framework:
        The collaboration framework under evaluation.
    mediators:
        Mediators to measure (process variables). Defaults to the built-ins.
    metrics:
        Performance metrics to measure (the DV). Defaults to quality,
        efficiency and safety.
    seed:
        Random seed for reproducibility of stochastic actors.
    """

    def __init__(
        self,
        framework: HMCFramework,
        mediators: Optional[list[MediatorBase]] = None,
        metrics: Optional[list[PerformanceMetric]] = None,
        seed: Optional[int] = None,
    ) -> None:
        from .mediators import (
            CognitiveLoadMediator,
            DecisionTimeMediator,
            FatigueMediator,
            HandoverAccuracyMediator,
        )
        from .performance import EfficiencyMetric, QualityMetric, SafetyMetric

        self.framework = framework
        self.seed = seed
        self.rng = random.Random(seed)
        self.mediators = MediatorRegistry(
            mediators
            or [
                FatigueMediator(framework.metaknowledge),
                CognitiveLoadMediator(framework.metaknowledge),
                DecisionTimeMediator(framework.metaknowledge),
                HandoverAccuracyMediator(framework.metaknowledge),
            ]
        )
        self.metrics = MetricSet("performance")
        for metric in metrics or [
            QualityMetric(framework.metaknowledge),
            EfficiencyMetric(),
            SafetyMetric(framework.metaknowledge),
        ]:
            self.metrics.add(metric)
        self.tracer = TraceRecorder()

    # -- evaluation ------------------------------------------------------------

    def evaluate_tasks(
        self,
        tasks: Sequence[TaskSpec],
        ai: Optional[AIModel] = None,
        expert: Optional[Expert] = None,
    ) -> EvaluationReport:
        """Run one task set once through the framework."""
        report = EvaluationReport(self.framework.name)
        for task in tasks:
            run = self._evaluate_one(task, ai, expert)
            report.runs.append(run)
            self.tracer.record_outcome(run.outcome)
        report.metadata = {"seed": self.seed, "type": "tasks"}
        return report

    def evaluate_repeated(
        self,
        task: TaskSpec,
        n_runs: int = 20,
        ai: Optional[AIModel] = None,
        expert: Optional[Expert] = None,
    ) -> EvaluationReport:
        """Run the *same* task ``n_runs`` times (stochastic actors)."""
        report = EvaluationReport(self.framework.name)
        for _ in range(n_runs):
            run = self._evaluate_one(task, ai, expert)
            report.runs.append(run)
            self.tracer.record_outcome(run.outcome)
        report.metadata = {"seed": self.seed, "n_runs": n_runs, "type": "repeated"}
        return report

    # -- internals -------------------------------------------------------------

    def _evaluate_one(
        self, task: TaskSpec, ai: Optional[AIModel], expert: Optional[Expert]
    ) -> RunResult:
        outcome = self.framework.run(task, ai=ai, expert=expert)
        mediators = {m.key: m.compute(outcome) for m in self.mediators}
        performance = {m.key: m.compute(outcome) for m in self.metrics}
        return RunResult(
            framework_name=self.framework.name,
            task_id=task.id,
            outcome=outcome,
            mediators=mediators,
            performance=performance,
        )
