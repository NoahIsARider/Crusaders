"""Tests for handover policies."""

import pytest

from crusaders.core.types import Role, StepContext, StepSpec, TaskSpec
from crusaders.metaknowledge import OrganizationalMetaknowledge
from crusaders.policies import (
    AlwaysAI,
    AlwaysExpert,
    CompositePolicy,
    ConfidencePolicy,
    HandoverPolicy,
    LoadAwarePolicy,
    PolicyDecision,
    RiskGatePolicy,
    SessionState,
)


def make_context(risk=0.0, complexity=0.5, requires_expert=False, controller=Role.AI, confidence=0.5, fatigue=0.0):
    task = TaskSpec("t", "t")
    step = StepSpec("s1", "step", complexity=complexity, risk=risk, requires_expert=requires_expert)
    session = SessionState(current_controller=controller, fatigue=fatigue)
    return StepContext(task, step, 0, state={}, current_controller=controller, ai_confidence=confidence), session


def bind(policy: HandoverPolicy, mk: OrganizationalMetaknowledge) -> HandoverPolicy:
    policy.bind(mk)
    return policy


class TestRiskGatePolicy:
    def test_expert_on_high_risk(self):
        policy = bind(RiskGatePolicy(base_threshold=0.5), OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.5}))
        ctx, session = make_context(risk=0.9)
        decision = policy.decide(ctx, session)
        assert decision.hand_over
        assert decision.direction is Role.EXPERT

    def test_ai_keeps_low_risk(self):
        policy = bind(RiskGatePolicy(base_threshold=0.5), OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.5}))
        ctx, session = make_context(risk=0.1)
        decision = policy.decide(ctx, session)
        assert not decision.hand_over

    def test_requires_expert_forces_handover(self):
        policy = bind(RiskGatePolicy(base_threshold=0.5), OrganizationalMetaknowledge())
        ctx, session = make_context(risk=0.0, requires_expert=True, controller=Role.AI)
        decision = policy.decide(ctx, session)
        assert decision.hand_over and decision.direction is Role.EXPERT

    def test_meta_knowledge_narrows_boundary(self):
        # narrow AI boundary -> lower effective threshold -> expert sooner
        narrow = bind(RiskGatePolicy(base_threshold=0.5), OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.3}))
        wide = bind(RiskGatePolicy(base_threshold=0.5), OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.9}))
        ctx, session = make_context(risk=0.45)
        assert narrow.decide(ctx, session).hand_over
        assert not wide.decide(ctx, session).hand_over


class TestConfidencePolicy:
    def test_expert_steps_in_on_low_confidence(self):
        policy = bind(ConfidencePolicy(floor=0.4), OrganizationalMetaknowledge())
        ctx, session = make_context(controller=Role.AI, confidence=0.2)
        decision = policy.decide(ctx, session)
        assert decision.hand_over and decision.direction is Role.EXPERT

    def test_no_handover_when_confident(self):
        policy = bind(ConfidencePolicy(floor=0.4), OrganizationalMetaknowledge())
        ctx, session = make_context(controller=Role.AI, confidence=0.8)
        assert not policy.decide(ctx, session).hand_over


class TestLoadAwarePolicy:
    def test_hands_back_to_ai_on_high_fatigue(self):
        policy = bind(LoadAwarePolicy(fatigue_ceiling=0.7), OrganizationalMetaknowledge())
        ctx, session = make_context(controller=Role.EXPERT, fatigue=0.9)
        decision = policy.decide(ctx, session)
        assert decision.hand_over and decision.direction is Role.AI

    def test_respects_session_limit(self):
        policy = bind(LoadAwarePolicy(), OrganizationalMetaknowledge(expert_capability={"max_steps_per_session": 3}))
        ctx = StepContext(TaskSpec("t", "t"), StepSpec("s1", "s"), 0, current_controller=Role.EXPERT)
        session = SessionState(current_controller=Role.EXPERT, expert_steps=4)
        decision = policy.decide(ctx, session)
        assert decision.hand_over and decision.direction is Role.AI


class TestTrivialPolicies:
    def test_always_ai(self):
        policy = bind(AlwaysAI(), OrganizationalMetaknowledge())
        ctx, session = make_context(controller=Role.EXPERT)
        decision = policy.decide(ctx, session)
        assert decision.hand_over and decision.direction is Role.AI

    def test_always_expert(self):
        policy = bind(AlwaysExpert(), OrganizationalMetaknowledge())
        ctx, session = make_context(controller=Role.AI)
        decision = policy.decide(ctx, session)
        assert decision.hand_over and decision.direction is Role.EXPERT


class TestCompositePolicy:
    def test_requires_sub_policies(self):
        with pytest.raises(ValueError):
            CompositePolicy([])

    def test_majority_ai(self):
        composite = CompositePolicy([AlwaysExpert(), AlwaysAI(), AlwaysAI()])
        composite.bind(OrganizationalMetaknowledge())
        ctx, session = make_context(controller=Role.AI)
        decision = composite.decide(ctx, session)
        assert not decision.hand_over  # AI keeps control, majority wants AI

    def test_majority_expert(self):
        composite = CompositePolicy([AlwaysExpert(), AlwaysExpert(), AlwaysAI()])
        composite.bind(OrganizationalMetaknowledge())
        ctx, session = make_context(controller=Role.AI)
        decision = composite.decide(ctx, session)
        assert decision.hand_over and decision.direction is Role.EXPERT

    def test_binds_sub_policies(self):
        sub = RiskGatePolicy()
        composite = CompositePolicy([sub])
        composite.bind(OrganizationalMetaknowledge())
        assert sub._metaknowledge is composite._metaknowledge

    def test_hands_back_to_ai_when_expert_controlled(self):
        composite = CompositePolicy([AlwaysAI(), AlwaysAI(), AlwaysExpert()])
        composite.bind(OrganizationalMetaknowledge())
        ctx, session = make_context(controller=Role.EXPERT)
        decision = composite.decide(ctx, session)
        assert decision.hand_over and decision.direction is Role.AI


class TestPolicyContract:
    def test_unbound_policy_meta_raises(self):
        policy = RiskGatePolicy()
        ctx, session = make_context(risk=0.9)
        with pytest.raises(RuntimeError):
            policy.decide(ctx, session)

    def test_invalid_threshold_rejected(self):
        with pytest.raises(ValueError):
            RiskGatePolicy(base_threshold=1.5)
        with pytest.raises(ValueError):
            ConfidencePolicy(floor=-0.1)
