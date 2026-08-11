"""Tests for core domain types."""

import pytest

from hmcforge.core.types import (
    HandoverEvent,
    HandoverState,
    Role,
    StepSpec,
    TaskSpec,
)


class TestRoles:
    def test_counterpart(self):
        assert Role.AI.counterpart is Role.EXPERT
        assert Role.EXPERT.counterpart is Role.AI


class TestStepSpec:
    def test_rejects_out_of_range_values(self):
        with pytest.raises(ValueError):
            StepSpec("s1", "x", complexity=1.2, risk=-0.1)
        with pytest.raises(ValueError):
            StepSpec("s1", "x", complexity=0.0, risk=1.5)


class TestTaskSpec:
    def test_add_step_and_risk(self):
        task = (
            TaskSpec("t1", "demo")
            .add_step(StepSpec("a", "a", risk=0.2))
            .add_step(StepSpec("b", "b", risk=0.5))
        )
        assert len(task.steps) == 2
        assert task.total_risk == pytest.approx(0.7)


class TestHandoverEvent:
    def test_defaults(self):
        event = HandoverEvent(
            timestamp=1.0, direction="ai->expert", trigger="policy", step_id="s1", reason="test"
        )
        assert event.outcome.value == "success"
        assert len(event.event_id) == 8

    def test_states(self):
        assert HandoverState.AI_CONTROL.value == "ai_control"
        assert HandoverState.TRANSFERRING.value == "transferring"
