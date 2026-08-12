"""Tests for performance metrics (quality, efficiency, safety)."""

import pytest

from crusaders.core.types import Role, StepSpec, TaskSpec
from crusaders.framework import HMCFramework
from crusaders.metaknowledge import OrganizationalMetaknowledge, RiskResponsibility
from crusaders.performance import EfficiencyMetric, MetricSet, QualityMetric, SafetyMetric
from crusaders.policies import AlwaysAI, AlwaysExpert


def run_with(controller_policy, steps):
    framework = HMCFramework(name="x", policies=[controller_policy])
    task = TaskSpec("t", "t")
    for spec in steps:
        task.add_step(spec)
    return framework.run(task)


class TestQualityMetric:
    def test_pass_rate(self):
        steps = [
            StepSpec("ok", "ok", complexity=0.1),
            StepSpec("bad", "bad", complexity=0.99),
        ]
        outcome = run_with(AlwaysAI(), steps)
        metric = QualityMetric().compute(outcome)
        assert metric.detail["pass_rate"] == pytest.approx(0.5)
        assert metric.value == pytest.approx(0.5)

    def test_series_is_quality_values(self):
        outcome = run_with(AlwaysAI(), [StepSpec("a", "a", complexity=0.3)])
        metric = QualityMetric().compute(outcome)
        assert len(metric.series) == 1


class TestEfficiencyMetric:
    def test_with_ideal_time(self):
        steps = [StepSpec("a", "a"), StepSpec("b", "b")]
        outcome = run_with(AlwaysAI(), steps)
        metric = EfficiencyMetric(ideal_time=1.0).compute(outcome)
        # decision latencies far exceed 1.0 -> efficiency close to 0
        assert metric.value < 0.5

    def test_without_ideal_time_uses_latency_fallback(self):
        steps = [StepSpec("a", "a")]
        outcome = run_with(AlwaysAI(), steps)
        metric = EfficiencyMetric().compute(outcome)
        assert 0.0 < metric.value <= 1.0

    def test_expert_time_share_reported(self):
        steps = [StepSpec("a", "a")]
        outcome = run_with(AlwaysExpert(), steps)
        metric = EfficiencyMetric().compute(outcome)
        assert metric.detail["expert_time_share"] > 0.0


class TestSafetyMetric:
    def test_ai_on_high_risk_is_penalised(self):
        mk = OrganizationalMetaknowledge(
            risk_responsibility=[RiskResponsibility(0.4, "ai"), RiskResponsibility(1.0, "expert")]
        )
        steps = [StepSpec("risky", "risky", risk=0.9)]
        outcome = run_with(AlwaysAI(), steps)
        metric = SafetyMetric(mk).compute(outcome)
        assert metric.value == pytest.approx(0.0)

    def test_expert_on_high_risk_is_safe(self):
        mk = OrganizationalMetaknowledge(
            risk_responsibility=[RiskResponsibility(0.4, "ai"), RiskResponsibility(1.0, "expert")]
        )
        steps = [StepSpec("risky", "risky", risk=0.9)]
        outcome = run_with(AlwaysExpert(), steps)
        metric = SafetyMetric(mk).compute(outcome)
        assert metric.value == pytest.approx(1.0)


class TestMetricSet:
    def test_register_and_iterate(self):
        ms = MetricSet()
        ms.add(QualityMetric()).add(EfficiencyMetric())
        assert ms.keys == ["quality", "efficiency"]
        assert len(list(ms)) == 2
