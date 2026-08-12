"""Tests for the simulation runner and report building."""

import json

import pytest

from crusaders.core.types import StepSpec, TaskSpec
from crusaders.framework import HMCFramework
from crusaders.observability import EvaluationReport, TraceRecorder
from crusaders.policies import AlwaysAI, AlwaysExpert, RiskGatePolicy
from crusaders.runner import SimulationRunner


def task(n=3):
    t = TaskSpec("t1", "demo")
    for i in range(n):
        t.add_step(StepSpec(f"s{i}", f"step {i}", complexity=0.2 + 0.1 * i, risk=0.1 * i))
    return t


class TestRunner:
    def test_evaluate_tasks(self):
        framework = HMCFramework(name="f", policies=[RiskGatePolicy(base_threshold=0.5)])
        runner = SimulationRunner(framework, seed=1)
        report = runner.evaluate_tasks([task(), task(2)])
        assert report.framework_name == "f"
        assert report.n_runs == 2
        assert set(report.aggregated().keys()) == {
            "fatigue",
            "cognitive_load",
            "decision_time",
            "handover_accuracy",
            "quality",
            "efficiency",
            "safety",
        }

    def test_evaluate_repeated_is_stochastic_but_bounded(self):
        framework = HMCFramework(name="f")
        runner = SimulationRunner(framework, seed=42)
        report = runner.evaluate_repeated(task(), n_runs=10)
        assert report.n_runs == 10
        for key, value in report.aggregated().items():
            if key == "decision_time":  # seconds, not a ratio
                assert value > 0
                continue
            assert 0.0 <= value <= 1.0

    def test_deterministic_with_seed(self):
        framework = HMCFramework(name="f")
        r1 = SimulationRunner(framework, seed=3).evaluate_repeated(task(), n_runs=5)
        r2 = SimulationRunner(HMCFramework(name="f"), seed=3).evaluate_repeated(task(), n_runs=5)
        assert r1.aggregated() == r2.aggregated()

    def test_custom_mediator_and_metric(self):
        from crusaders.mediators import MediatorBase, MetricResult
        from crusaders.performance import PerformanceMetric

        class MyMediator(MediatorBase):
            key = "trust"
            label = "Trust"
            higher_is_better = True

            def compute(self, outcome):
                return MetricResult("trust", 0.7, "Trust", True, series=[0.7])

        class MyMetric(PerformanceMetric):
            key = "alignment"
            label = "Alignment"

            def compute(self, outcome):
                return MetricResult("alignment", 0.8, "Alignment", True)

        runner = SimulationRunner(
            HMCFramework(name="f"),
            mediators=[MyMediator()],
            metrics=[MyMetric()],
        )
        report = runner.evaluate_tasks([task(1)])
        assert "trust" in report.aggregated()
        assert "alignment" in report.aggregated()


class TestReport:
    def test_to_dict_and_json_roundtrip(self, tmp_path):
        framework = HMCFramework(name="f", policies=[AlwaysExpert()])
        report = SimulationRunner(framework, seed=1).evaluate_tasks([task(2)])
        path = tmp_path / "report.json"
        text = report.to_json(str(path))
        assert path.exists()
        assert json.loads(text)["framework"] == "f"
        assert json.loads(path.read_text())["n_runs"] == 1

    def test_to_markdown(self):
        framework = HMCFramework(name="f")
        report = SimulationRunner(framework, seed=1).evaluate_tasks([task(2)])
        md = report.to_markdown()
        assert "# Evaluation report: f" in md
        assert "Aggregated scores" in md
        assert "| metric |" in md

    def test_aggregated_empty(self):
        report = EvaluationReport("none")
        assert report.aggregated() == {}
        assert report.to_dict()["n_runs"] == 0


class TestTraceRecorder:
    def test_records_events_and_runs(self):
        framework = HMCFramework(name="f", policies=[AlwaysExpert()])
        recorder = TraceRecorder()
        recorder.attach(framework)
        outcome = framework.run(task(2))
        recorder.record_outcome(outcome)
        data = recorder.export()
        assert len(data["events"]) == 1
        assert data["events"][0]["direction"] == "ai->expert"
        assert len(data["runs"]) == 1

    def test_to_json(self, tmp_path):
        framework = HMCFramework(name="f")
        recorder = TraceRecorder()
        recorder.attach(framework)
        recorder.record_outcome(framework.run(task(1)))
        path = tmp_path / "trace.json"
        recorder.to_json(str(path))
        assert path.exists()
