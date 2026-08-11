"""Tests for organisational meta-knowledge (the moderator)."""

import pytest

from hmcforge.metaknowledge import OrganizationalMetaknowledge, RiskResponsibility


class TestRiskResponsibility:
    def test_clamps_threshold(self):
        assert RiskResponsibility(1.0, "expert").threshold == 1.0
        with pytest.raises(ValueError):
            RiskResponsibility(1.2, "expert")

    def test_rejects_unknown_role(self):
        with pytest.raises(ValueError):
            RiskResponsibility(0.5, "robot")


class TestMetaKnowledge:
    def test_default_responsibility_is_expert(self):
        mk = OrganizationalMetaknowledge()
        assert mk.responsibility_for(0.0) == "expert"
        assert mk.responsibility_for(1.0) == "expert"

    def test_band_lookup(self):
        mk = OrganizationalMetaknowledge(
            risk_responsibility=[
                RiskResponsibility(0.3, "ai"),
                RiskResponsibility(0.8, "shared"),
                RiskResponsibility(1.0, "expert"),
            ]
        )
        assert mk.responsibility_for(0.1) == "ai"
        assert mk.responsibility_for(0.3) == "ai"
        assert mk.responsibility_for(0.5) == "shared"
        assert mk.responsibility_for(0.9) == "expert"

    def test_accessors_with_defaults(self):
        mk = OrganizationalMetaknowledge()
        assert mk.max_ai_complexity() == 0.7
        assert mk.expert_session_limit() == 6
        assert mk.handover_overhead_budget() == 5.0

    def test_update_returns_self_and_bumps_version(self):
        mk = OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.8})
        returned = mk.update_from({"ai_boundary": {"max_complexity": 0.5}})
        assert returned is mk
        assert mk.version == 1
        assert mk.max_ai_complexity() == 0.5

    def test_update_merges_nested_maps(self):
        mk = OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.8, "keep": True})
        mk.update_from({"ai_boundary": {"max_complexity": 0.4}})
        assert mk.ai_boundary == {"max_complexity": 0.4, "keep": True}

    def test_update_rejects_unknown_field(self):
        mk = OrganizationalMetaknowledge()
        with pytest.raises(KeyError):
            mk.update_from({"nope": 1})

    def test_update_accepts_dict_for_risk_bands(self):
        mk = OrganizationalMetaknowledge()
        mk.update_from({"risk_responsibility": [{"threshold": 0.5, "role": "ai"}]})
        assert mk.risk_responsibility[0].role == "ai"

    def test_clone_is_independent(self):
        mk = OrganizationalMetaknowledge(ai_boundary={"max_complexity": 0.8})
        clone = mk.clone()
        clone.update_from({"ai_boundary": {"max_complexity": 0.2}})
        assert mk.max_ai_complexity() == 0.8
        assert clone.max_ai_complexity() == 0.2
        assert mk.version == 0

    def test_lessons_can_be_read_back(self):
        mk = OrganizationalMetaknowledge()
        mk.update_from({"lessons": ["a", "b"]})
        assert mk.lessons == ["a", "b"]

    def test_summary_contains_key_facts(self):
        mk = OrganizationalMetaknowledge()
        summary = mk.summary()
        assert "version" in summary
        assert "risk_responsibility" in summary
        assert summary["n_lessons"] == 0
