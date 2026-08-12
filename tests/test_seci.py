"""Tests for the SECI feedback engine."""

import pytest

from crusaders.mediators import MetricResult
from crusaders.metaknowledge import OrganizationalMetaknowledge
from crusaders.observability import EvaluationReport, RunResult
from crusaders.seci import KnowledgeUpdate, Lesson, SECIEngine


def report_with(aggregate: dict[str, float], n_runs=3) -> EvaluationReport:
    report = EvaluationReport("f")
    for i in range(n_runs):
        outcome = type(
            "O", (), {"n_handovers": 1, "passed_steps": 2, "n_steps": 3, "elapsed": 1.0}
        )()
        report.runs.append(
            RunResult(
                framework_name="f",
                task_id=f"t{i}",
                outcome=outcome,
                mediators={k: MetricResult(k, v, k, True) for k, v in aggregate.items()},
                performance={},
            )
        )
    return report


class TestKnowledgeUpdate:
    def test_apply_updates_metaknowledge(self):
        update = KnowledgeUpdate(
            lessons=[Lesson("externalization", "lesson one")],
            patch={"ai_boundary": {"max_complexity": 0.4}},
        )
        mk = OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.7})
        updated = update.apply(mk)
        assert updated.max_ai_complexity() == 0.4
        assert updated.lessons == ["lesson one"]
        assert mk.max_ai_complexity() == 0.7  # original untouched

    def test_apply_dedupes_lessons(self):
        update = KnowledgeUpdate(
            lessons=[Lesson("externalization", "dup"), Lesson("externalization", "dup")]
        )
        mk = OrganizationalMetaknowledge()
        assert update.apply(mk).lessons == ["dup"]


class TestSECIEngine:
    def test_invalid_learning_rate(self):
        with pytest.raises(ValueError):
            SECIEngine(learning_rate=0.0)
        with pytest.raises(ValueError):
            SECIEngine(learning_rate=1.5)

    def test_run_produces_lessons_and_patch(self):
        engine = SECIEngine(OrganizationalMetaknowledge(), learning_rate=0.2)
        update = engine.run(report_with({"fatigue": 0.9, "handover_accuracy": 0.5}))
        assert update.lessons
        assert any(l.stage == "socialization" for l in update.lessons)
        assert any(l.stage == "externalization" for l in update.lessons)

    def test_high_fatigue_narrows_ai_boundary(self):
        mk = OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.7})
        engine = SECIEngine(mk, learning_rate=0.5)
        update = engine.run(report_with({"fatigue": 0.9, "safety": 0.5}))
        assert "ai_boundary" in update.patch
        assert update.patch["ai_boundary"]["max_complexity"] < 0.7

    def test_low_fatigue_grows_expert_session(self):
        mk = OrganizationalMetaknowledge(expert_capability={"max_steps_per_session": 4})
        engine = SECIEngine(mk, learning_rate=0.5)
        update = engine.run(report_with({"fatigue": 0.1, "quality": 0.9}))
        assert update.patch["expert_capability"]["max_steps_per_session"] == 5

    def test_recommendations_produced_under_stress(self):
        engine = SECIEngine(learning_rate=0.2)
        update = engine.run(report_with({"fatigue": 0.9}))
        assert "load_aware.fatigue_ceiling" in update.recommendations

    def test_empty_report_is_safe(self):
        engine = SECIEngine()
        update = engine.run(EvaluationReport("none"))
        assert update.lessons == []
