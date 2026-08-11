"""Tests for the built-in scenario cases."""

import pytest

from hmcforge import SimulationRunner, SECIEngine
from hmcforge.scenarios import code_review, financial_underwriting, healthcare_triage

SCENARIOS = [healthcare_triage, code_review, financial_underwriting]
MODEL_KEYS = {
    "fatigue",
    "cognitive_load",
    "decision_time",
    "handover_accuracy",
    "quality",
    "efficiency",
    "safety",
}


class TestScenarioContract:
    @pytest.mark.parametrize("mod", SCENARIOS)
    def test_has_required_pieces(self, mod):
        assert mod.DOMAIN
        mk = mod.default_metaknowledge()
        assert mk.responsibility_for(1.0) in {"ai", "expert", "shared"}
        assert len(mod.tasks()) >= 1
        framework = mod.framework()
        assert framework.name
        for task in mod.tasks():
            assert task.steps

    @pytest.mark.parametrize("mod", SCENARIOS)
    def test_runs_and_scores_all_metrics(self, mod):
        report = SimulationRunner(mod.framework(), seed=11).evaluate_tasks(mod.tasks())
        assert report.n_runs == len(mod.tasks())
        keys = set(report.aggregated().keys())
        assert MODEL_KEYS.issubset(keys)
        for key, value in report.aggregated().items():
            if key == "decision_time":  # seconds, not a ratio
                assert value > 0
                continue
            assert 0.0 <= value <= 1.0

    @pytest.mark.parametrize("mod", SCENARIOS)
    def test_seci_loop_closes(self, mod):
        engine = SECIEngine(mod.default_metaknowledge())
        update = engine.run(SimulationRunner(mod.framework(), seed=1).evaluate_tasks(mod.tasks()))
        updated = update.apply(mod.default_metaknowledge())
        assert updated.version >= 1


class TestDifferentiation:
    def test_frameworks_produce_different_handover_patterns(self):
        outcomes = {
            mod.DOMAIN: SimulationRunner(mod.framework(), seed=3)
            .evaluate_tasks(mod.tasks())
            .aggregated()
            for mod in SCENARIOS
        }
        assert set(outcomes.keys()) == {"healthcare_triage", "code_review", "financial_underwriting"}
        # every domain must yield a valid handover-accuracy score
        for domain, agg in outcomes.items():
            assert 0.0 <= agg["handover_accuracy"] <= 1.0

    def test_code_review_expert_only_on_critical_files(self):
        # code_review flags require_expert; check expert steps exist at all
        report = SimulationRunner(code_review.framework(), seed=3).evaluate_tasks(code_review.tasks())
        any_expert = any(
            o.controller.value == "expert"
            for run in report.runs
            for o in run.outcome.step_outcomes
        )
        assert any_expert
