"""Tests for the actor adapters."""

import pytest

from crusaders import adapters
from crusaders.adapters import RuleBasedAI, SimulatedExpert
from crusaders.core.types import Role, StepSpec
from crusaders.policies import SessionState


class TestRuleBasedAI:
    def test_quality_decreases_with_complexity(self):
        ai = RuleBasedAI()
        easy = ai.act(StepSpec("e", "e", complexity=0.1), SessionState())
        hard = ai.act(StepSpec("h", "h", complexity=0.95), SessionState())
        assert easy.quality_estimate > hard.quality_estimate
        assert easy.confidence > hard.confidence

    def test_values_in_bounds(self):
        ai = RuleBasedAI()
        decision = ai.act(StepSpec("s", "s", complexity=0.99), SessionState())
        assert 0.0 <= decision.quality_estimate <= 1.0
        assert decision.role is Role.AI

    def test_latency_positive(self):
        decision = RuleBasedAI(base_latency=2.0).act(StepSpec("s", "s"), SessionState())
        assert decision.latency > 0


class TestSimulatedExpert:
    def test_rejects_bad_accuracy(self):
        with pytest.raises(ValueError):
            SimulatedExpert(accuracy=1.5)

    def test_quality_drops_with_fatigue(self):
        expert = SimulatedExpert(accuracy=0.9, fatigue_penalty=0.4)
        fresh = expert.act(StepSpec("s", "s"), SessionState(fatigue=0.0))
        tired = expert.act(StepSpec("s", "s"), SessionState(fatigue=0.8))
        assert fresh.quality_estimate > tired.quality_estimate

    def test_fatigue_never_drives_quality_below_floor(self):
        expert = SimulatedExpert(accuracy=0.9, fatigue_penalty=1.0)
        decision = expert.act(StepSpec("s", "s"), SessionState(fatigue=1.0))
        assert decision.quality_estimate >= 0.05

    def test_role_and_metadata(self):
        decision = SimulatedExpert(name="dr").act(StepSpec("s", "s"), SessionState())
        assert decision.role is Role.EXPERT
        assert decision.metadata["expert"] == "dr"


class TestOpenAIAdapter:
    def test_missing_dependency_or_key_raises(self, monkeypatch):
        # Without the optional 'openai' package an ImportError is raised;
        # with it installed but no key configured a ValueError is raised.
        monkeypatch.delenv("USER_LLM_API_KEY", raising=False)
        with pytest.raises((ImportError, ValueError)):
            adapters.OpenAIAdapter()

    def test_extract_number(self):
        assert adapters._extract_number('{"confidence": 0.42}', "confidence", 0.5) == 0.42
        assert adapters._extract_number("quality=0.3", "quality", 0.5) == 0.3
        assert adapters._extract_number("nothing here", "confidence", 0.5) == 0.5
        assert adapters._extract_number("confidence: 2.5", "confidence", 0.5) == 1.0
        assert adapters._extract_number("confidence: -1", "confidence", 0.5) == 0.5
