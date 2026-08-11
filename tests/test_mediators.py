"""Tests for mediators (process variables)."""

import pytest

from hmcforge.core.types import Role, StepSpec, TaskSpec
from hmcforge.framework import HMCFramework
from hmcforge.metaknowledge import OrganizationalMetaknowledge, RiskResponsibility
from hmcforge.mediators import (
    CognitiveLoadMediator,
    DecisionTimeMediator,
    FatigueMediator,
    HandoverAccuracyMediator,
    MediatorRegistry,
)
from hmcforge.policies import AlwaysExpert


def expert_framework_task():
    framework = HMCFramework(name="exp", policies=[AlwaysExpert()])
    task = (
        TaskSpec("t", "t")
        .add_step(StepSpec("a", "a", complexity=0.3, risk=0.2))
        .add_step(StepSpec("b", "b", complexity=0.6, risk=0.8))
    )
    return framework, task


class TestFatigueAndLoad:
    def test_expert_driven_task_builds_fatigue(self):
        framework, task = expert_framework_task()
        outcome = framework.run(task)
        fatigue = FatigueMediator().compute(outcome)
        load = CognitiveLoadMediator().compute(outcome)
        assert 0.0 <= fatigue.value <= 1.0
        assert 0.0 <= load.value <= 1.0
        assert len(fatigue.series) == 2

    def test_ai_only_task_keeps_load_low(self):
        framework = HMCFramework(name="ai")
        task = (
            TaskSpec("t", "t")
            .add_step(StepSpec("a", "a", complexity=0.2))
            .add_step(StepSpec("b", "b", complexity=0.3))
        )
        outcome = framework.run(task)
        fatigue = FatigueMediator().compute(outcome)
        assert fatigue.value < 0.1


class TestDecisionTime:
    def test_mean_latency(self):
        framework, task = expert_framework_task()
        outcome = framework.run(task)
        metric = DecisionTimeMediator().compute(outcome)
        assert metric.series == [pytest.approx(o.decision.latency) for o in outcome.step_outcomes]
        assert metric.detail["handover_overhead"] >= 0


class TestHandoverAccuracy:
    def test_matches_responsibility_map(self):
        mk = OrganizationalMetaknowledge(
            risk_responsibility=[RiskResponsibility(0.5, "ai"), RiskResponsibility(1.0, "expert")]
        )
        framework, task = expert_framework_task()
        outcome = framework.run(task)
        metric = HandoverAccuracyMediator(mk).compute(outcome)
        # step b has risk 0.8 -> expert responsible; step a risk 0.2 -> ai. Expert does all.
        assert metric.value == 0.5

    def test_perfect_when_roles_align(self):
        mk = OrganizationalMetaknowledge(
            risk_responsibility=[RiskResponsibility(0.5, "ai"), RiskResponsibility(1.0, "expert")]
        )
        framework, task = expert_framework_task()
        outcome = framework.run(task)
        metric = HandoverAccuracyMediator(mk).compute(outcome)
        assert 0.0 <= metric.value <= 1.0


class TestMediatorRegistry:
    def test_register_and_get(self):
        registry = MediatorRegistry([FatigueMediator(), CognitiveLoadMediator()])
        assert set(registry.keys) == {"fatigue", "cognitive_load"}
        assert registry.get("fatigue") is not None
        assert registry.get("missing") is None

    def test_iteration(self):
        registry = MediatorRegistry()
        registry.add(FatigueMediator())
        assert len(list(registry)) == 1

    def test_metric_result_render(self):
        result = FatigueMediator().compute(expert_framework_task()[0].run(expert_framework_task()[1]))
        assert "Mean human fatigue" in result.render
