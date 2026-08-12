"""Tests for the framework base class."""

import pytest

from crusaders.adapters import RuleBasedAI, SimulatedExpert
from crusaders.core.types import HandoverDirection, Role, StepSpec, TaskSpec
from crusaders.framework import HMCFramework, HandoverDecision
from crusaders.metaknowledge import OrganizationalMetaknowledge
from crusaders.policies import HandoverPolicy, PolicyDecision, RiskGatePolicy, SessionState


def simple_task(n=3):
    task = TaskSpec("t1", "demo")
    for i in range(n):
        task.add_step(StepSpec(f"s{i}", f"step {i}", complexity=0.3, risk=0.1 * i))
    return task


class AlwaysExpertFramework(HMCFramework):
    def decide_handover(self, step, session):
        if session.current_controller is Role.AI:
            return HandoverDecision(Role.EXPERT, reason="always expert")
        return HandoverDecision(Role.EXPERT, reason="keep")


class TestFrameworkBasics:
    def test_runs_with_default_actors(self):
        framework = HMCFramework(name="plain")
        outcome = framework.run(simple_task())
        assert outcome.n_steps == 3
        assert len(outcome.step_outcomes) == 3
        assert outcome.n_handovers == 0  # plain keeps AI control

    def test_custom_subclass_handover(self):
        outcome = AlwaysExpertFramework(name="exp").run(simple_task())
        assert all(o.controller is Role.EXPERT for o in outcome.step_outcomes)
        assert outcome.n_handovers == 1  # one ai->expert at the first step

    def test_elapsed_is_simulated_time(self):
        ai = RuleBasedAI(base_latency=2.0)
        expert = SimulatedExpert(latency=5.0)
        outcome = AlwaysExpertFramework().run(simple_task(2), ai=ai, expert=expert)
        expected = sum(o.decision.latency for o in outcome.step_outcomes) + outcome.metadata["overhead_seconds"]
        assert outcome.elapsed == pytest.approx(expected)
        assert outcome.expert_active_seconds > 0

    def test_handover_direction_is_recorded(self):
        outcome = AlwaysExpertFramework().run(simple_task(2))
        assert outcome.events[0].direction is HandoverDirection.AI_TO_EXPERT

    def test_policy_driven_handover(self):
        mk = OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.3})
        framework = HMCFramework(name="gated", metaknowledge=mk, policies=[RiskGatePolicy(base_threshold=0.4)])
        task = (
            TaskSpec("t", "t")
            .add_step(StepSpec("easy", "easy", risk=0.1))
            .add_step(StepSpec("hard", "hard", risk=0.9))
        )
        outcome = framework.run(task)
        assert outcome.step_outcomes[0].controller is Role.AI
        assert outcome.step_outcomes[1].controller is Role.EXPERT

    def test_observers_receive_handover_events(self):
        seen = []
        framework = AlwaysExpertFramework()
        framework.add_observer(lambda event, ctx: seen.append(event))
        framework.run(simple_task(2))
        assert len(seen) == 1
        assert seen[0].step_id == "s0"

    def test_step_evaluator_is_honoured(self):
        def always_fail(decision, spec):
            return False

        framework = HMCFramework(name="strict", step_evaluator=always_fail)
        outcome = framework.run(simple_task(2))
        assert outcome.successful is False
        assert outcome.passed_steps == 0

    def test_session_snapshots_are_attached(self):
        framework = AlwaysExpertFramework()
        outcome = framework.run(simple_task(2))
        for step_outcome in outcome.step_outcomes:
            assert step_outcome.session is not None
            assert step_outcome.session.expert_steps >= 1

    def test_metaknowledge_overhead_budget_used(self):
        mk = OrganizationalMetaknowledge(handover_timing={"handover_overhead_budget": 3.0})
        framework = AlwaysExpertFramework(name="ow", metaknowledge=mk)
        assert framework.handover_overhead == 3.0

    def test_empty_task(self):
        outcome = HMCFramework().run(TaskSpec("empty", "empty"))
        assert outcome.n_steps == 0
        assert outcome.successful


class TestDslPolicies:
    def test_policy_object_usable_instead_of_list(self):
        class OnePolicyFramework(HMCFramework):
            def decide_handover(self, step, session):
                return HandoverDecision(Role.EXPERT)

        # ensure no exception constructing with a single policy object path
        outcome = OnePolicyFramework().run(simple_task(1))
        assert outcome.n_steps == 1
