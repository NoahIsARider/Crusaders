"""FastAPI backend powering the Crusaders visual studio.

Exposes the HMC framework as JSON: load preset scenarios, compose policies and
meta-knowledge, run deterministic simulations and return a full evaluation
report plus SECI feedback. The GUI in ``gui/`` talks to nothing else.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .core.types import Role, StepSpec, TaskSpec
from .framework import HMCFramework
from .metaknowledge import OrganizationalMetaknowledge, RiskResponsibility
from .observability import EvaluationReport
from .policies import (
    AlwaysAI,
    AlwaysExpert,
    CompositePolicy,
    ConfidencePolicy,
    HandoverPolicy,
    LoadAwarePolicy,
    RiskGatePolicy,
)
from .runner import SimulationRunner
from .seci import SECIEngine

app = FastAPI(title="Crusaders Studio", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Policy catalogue served to the frontend palette.
# --------------------------------------------------------------------------

POLICY_CATALOGUE: list[dict[str, Any]] = [
    {
        "type": "risk_gate",
        "label": "Risk Gate",
        "icon": "shield",
        "description": "Escalate to the expert when step risk crosses the gate. Steps that require an expert are always delegated.",
        "params": [
            {
                "key": "base_threshold",
                "label": "Risk threshold",
                "kind": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "help": "Steps above this risk are handled by the expert",
            }
        ],
    },
    {
        "type": "confidence",
        "label": "Confidence Gate",
        "icon": "gauge",
        "description": "Hand over to the expert when the AI's confidence drops below the floor.",
        "params": [
            {
                "key": "floor",
                "label": "Confidence floor",
                "kind": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.4,
                "help": "Below this AI confidence the expert takes over",
            }
        ],
    },
    {
        "type": "load_aware",
        "label": "Load Aware",
        "icon": "pulse",
        "description": "Give the human a breather by routing work back to the AI when fatigue climbs toward the ceiling.",
        "params": [
            {
                "key": "fatigue_ceiling",
                "label": "Fatigue ceiling",
                "kind": "slider",
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "default": 0.8,
                "help": "Switch to the AI when expert fatigue reaches this",
            }
        ],
    },
    {
        "type": "always_ai",
        "label": "Always AI",
        "icon": "bot",
        "description": "Baseline: every step is handled by the AI.",
        "params": [],
    },
    {
        "type": "always_expert",
        "label": "Always Expert",
        "icon": "user",
        "description": "Baseline: every step is handled by the expert.",
        "params": [],
    },
    {
        "type": "composite",
        "label": "Composite",
        "icon": "layers",
        "description": "Let several sub-policies vote; a handover happens only when the majority agrees.",
        "params": [
            {
                "key": "majority",
                "label": "Majority ratio",
                "kind": "slider",
                "min": 0.1,
                "max": 1.0,
                "step": 0.05,
                "default": 0.5,
                "help": "Fraction of sub-policies that must vote to hand over",
            }
        ],
        "nested": "policies",
    },
]

METRIC_CATALOGUE: list[dict[str, Any]] = [
    {"key": "quality", "label": "Quality", "higher_is_better": True, "kind": "outcome"},
    {"key": "efficiency", "label": "Efficiency", "higher_is_better": True, "kind": "outcome"},
    {"key": "safety", "label": "Safety", "higher_is_better": True, "kind": "outcome"},
    {"key": "fatigue", "label": "Fatigue", "higher_is_better": False, "kind": "process"},
    {"key": "cognitive_load", "label": "Cognitive load", "higher_is_better": False, "kind": "process"},
    {"key": "decision_time", "label": "Decision time", "higher_is_better": False, "kind": "process"},
    {"key": "handover_accuracy", "label": "Handover accuracy", "higher_is_better": True, "kind": "process"},
]

# --------------------------------------------------------------------------
# Request / response models.
# --------------------------------------------------------------------------


class SimulateRequest(BaseModel):
    framework_name: str = "my-framework"
    metaknowledge: dict[str, Any] = {}
    policies: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []
    mode: str = "tasks"  # "tasks" | "repeated"
    n_runs: int = 1
    seed: int = 3
    learning_rate: float = 0.2


# --------------------------------------------------------------------------
# Builders: raw JSON -> framework objects.
# --------------------------------------------------------------------------


def _clamp(value: Any, name: str, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not lo <= num <= hi:
        raise ValueError(f"{name} must be within [{lo}, {hi}]")
    return num


def _build_metaknowledge(raw: dict[str, Any]) -> OrganizationalMetaknowledge:
    raw = raw or {}
    bands: list[RiskResponsibility] = []
    for band in raw.get("risk_responsibility", []) or []:
        bands.append(
            RiskResponsibility(
                threshold=_clamp(band.get("threshold", 1.0), "risk band threshold"),
                role=str(band.get("role", "expert")),
            )
        )
    if not bands:
        bands.append(RiskResponsibility(1.0, "expert"))
    return OrganizationalMetaknowledge(
        ai_boundary=dict(raw.get("ai_boundary", {}) or {}),
        expert_capability=dict(raw.get("expert_capability", {}) or {}),
        risk_responsibility=bands,
        handover_timing=dict(raw.get("handover_timing", {}) or {}),
    )


def _build_policy(raw: dict[str, Any]) -> HandoverPolicy:
    ptype = raw.get("type")
    if ptype == "risk_gate":
        return RiskGatePolicy(
            base_threshold=_clamp(raw.get("base_threshold", 0.5), "risk threshold")
        )
    if ptype == "confidence":
        return ConfidencePolicy(floor=_clamp(raw.get("floor", 0.4), "confidence floor"))
    if ptype == "load_aware":
        return LoadAwarePolicy(
            fatigue_ceiling=_clamp(raw.get("fatigue_ceiling", 0.8), "fatigue ceiling")
        )
    if ptype == "always_ai":
        return AlwaysAI()
    if ptype == "always_expert":
        return AlwaysExpert()
    if ptype == "composite":
        children = [_build_policy(p) for p in raw.get("policies", []) or []]
        if not children:
            raise ValueError("a composite policy needs at least one sub-policy")
        return CompositePolicy(
            children,
            majority=_clamp(raw.get("majority", 0.5), "majority ratio", 0.0, 1.0),
        )
    raise ValueError(f"unknown policy type: {ptype!r}")


def _build_tasks(raw: list[dict[str, Any]]) -> list[TaskSpec]:
    tasks: list[TaskSpec] = []
    for task_raw in raw or []:
        task = TaskSpec(
            id=str(task_raw.get("id") or f"task-{len(tasks) + 1}"),
            title=str(task_raw.get("title") or "Untitled task"),
            ideal_time=task_raw.get("ideal_time"),
        )
        for step_raw in task_raw.get("steps", []) or []:
            task.add_step(
                StepSpec(
                    id=str(step_raw.get("id") or f"{task.id}-s{len(task.steps) + 1}"),
                    description=str(step_raw.get("description") or "Untitled step"),
                    complexity=_clamp(step_raw.get("complexity", 0.5), "complexity"),
                    risk=_clamp(step_raw.get("risk", 0.2), "risk"),
                    requires_expert=bool(step_raw.get("requires_expert", False)),
                )
            )
        if task.steps:
            tasks.append(task)
    return tasks


def _run_to_dict(run: Any) -> dict[str, Any]:
    """Serialise one RunResult into the report payload."""
    outcome = run.outcome
    return {
        "task": run.task_id,
        "elapsed": outcome.elapsed,
        "successful": outcome.successful,
        "n_steps": outcome.n_steps,
        "passed_steps": outcome.passed_steps,
        "n_handovers": outcome.n_handovers,
        "mediators": {k: m.value for k, m in run.mediators.items()},
        "performance": {k: m.value for k, m in run.performance.items()},
        "handover_events": [
            {
                "timestamp": round(e.timestamp, 3),
                "direction": e.direction.value,
                "trigger": e.trigger.value,
                "step_id": e.step_id,
                "reason": e.reason,
                "duration": round(e.duration, 3),
            }
            for e in outcome.events
        ],
        "steps": [
            {
                "step_id": o.step.id,
                "description": o.step.description,
                "complexity": o.step.complexity,
                "risk": o.step.risk,
                "requires_expert": o.step.requires_expert,
                "controller": o.controller.value,
                "passed": o.passed,
                "quality_estimate": round(o.decision.quality_estimate, 3),
                "confidence": round(o.decision.confidence, 3),
                "latency": round(o.decision.latency, 3),
            }
            for o in outcome.step_outcomes
        ],
    }


# --------------------------------------------------------------------------
# Routes.
# --------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    return {
        "policies": POLICY_CATALOGUE,
        "metrics": METRIC_CATALOGUE,
        "roles": ["ai", "expert"],
        "presets": [p["id"] for p in _presets()],
    }


def _presets() -> list[dict[str, Any]]:
    def _mk(domain: str, name: str, tagline: str, meta, policies, tasks) -> dict[str, Any]:
        return {
            "id": domain,
            "name": name,
            "tagline": tagline,
            "framework_name": domain,
            "metaknowledge": meta,
            "policies": policies,
            "tasks": tasks,
        }

    return [
        _mk(
            "healthcare_triage",
            "ED Triage",
            "Human-in-the-loop safety net - clinician owns high-risk steps",
            {
                "ai_boundary": {
                    "max_complexity": 0.5,
                    "allowed_domains": ["intake", "vital_signs", "scheduling"],
                },
                "expert_capability": {
                    "max_steps_per_session": 5,
                    "strengths": ["differential_diagnosis", "triage_escalation"],
                },
                "risk_responsibility": [
                    {"threshold": 0.35, "role": "ai"},
                    {"threshold": 0.7, "role": "shared"},
                    {"threshold": 1.0, "role": "expert"},
                ],
                "handover_timing": {"prefer_early": 0.2, "handover_overhead_budget": 0.8},
            },
            [{"type": "risk_gate", "base_threshold": 0.35}],
            [
                {
                    "id": "ed-001",
                    "title": "Low-acuity outpatient",
                    "steps": [
                        {"id": "ed-001-vitals", "description": "Capture and parse vital signs", "complexity": 0.25, "risk": 0.1},
                        {"id": "ed-001-history", "description": "Extract chief complaint and history", "complexity": 0.45, "risk": 0.3},
                        {"id": "ed-001-flags", "description": "Screen for red-flag symptoms", "complexity": 0.6, "risk": 0.8, "requires_expert": True},
                        {"id": "ed-001-plan", "description": "Draft initial triage disposition", "complexity": 0.5, "risk": 0.2, "requires_expert": True},
                    ],
                },
                {
                    "id": "ed-002",
                    "title": "Chest pain workup",
                    "steps": [
                        {"id": "ed-002-vitals", "description": "Capture and parse vital signs", "complexity": 0.25, "risk": 0.1},
                        {"id": "ed-002-history", "description": "Extract chief complaint and history", "complexity": 0.45, "risk": 0.3},
                        {"id": "ed-002-flags", "description": "Screen for red-flag symptoms", "complexity": 0.6, "risk": 0.8, "requires_expert": True},
                        {"id": "ed-002-plan", "description": "Draft initial triage disposition", "complexity": 0.5, "risk": 0.9, "requires_expert": True},
                    ],
                },
            ],
        ),
        _mk(
            "financial_underwriting",
            "Loan Underwriting",
            "Confidence-driven delegation - experts own judgement calls",
            {
                "ai_boundary": {
                    "max_complexity": 0.65,
                    "allowed_domains": ["ocr", "credit_scoring", "document_extraction"],
                },
                "expert_capability": {
                    "max_steps_per_session": 8,
                    "strengths": ["judgement", "policy_exceptions", "fraud_analysis"],
                },
                "risk_responsibility": [
                    {"threshold": 0.4, "role": "ai"},
                    {"threshold": 1.0, "role": "shared"},
                ],
                "handover_timing": {"prefer_early": 0.5, "handover_overhead_budget": 1.5},
            },
            [
                {
                    "type": "composite",
                    "majority": 0.5,
                    "policies": [
                        {"type": "risk_gate", "base_threshold": 0.55},
                        {"type": "confidence", "floor": 0.4},
                        {"type": "load_aware", "fatigue_ceiling": 0.8},
                    ],
                }
            ],
            [
                {
                    "id": "uw-101",
                    "title": "Prime auto loan",
                    "steps": [
                        {"id": "uw-101-extract", "description": "Extract applicant data from documents", "complexity": 0.35, "risk": 0.2},
                        {"id": "uw-101-score", "description": "Run credit scoring model", "complexity": 0.3, "risk": 0.25},
                        {"id": "uw-101-verify", "description": "Verify income and employment", "complexity": 0.55, "risk": 0.3},
                        {"id": "uw-101-approve", "description": "Decision memo and risk rating", "complexity": 0.45, "risk": 0.7},
                    ],
                },
                {
                    "id": "uw-102",
                    "title": "Self-employed income review",
                    "steps": [
                        {"id": "uw-102-extract", "description": "Extract applicant data from documents", "complexity": 0.35, "risk": 0.2},
                        {"id": "uw-102-score", "description": "Run credit scoring model", "complexity": 0.3, "risk": 0.25},
                        {"id": "uw-102-verify", "description": "Verify income and employment", "complexity": 0.55, "risk": 0.7},
                        {"id": "uw-102-approve", "description": "Decision memo and risk rating", "complexity": 0.8, "risk": 0.7},
                    ],
                },
            ],
        ),
        _mk(
            "code_review",
            "Code Review",
            "Efficiency-driven - engineers join for critical files",
            {
                "ai_boundary": {
                    "max_complexity": 0.7,
                    "allowed_domains": ["linting", "security_patterns", "test_gap_analysis"],
                },
                "expert_capability": {
                    "max_steps_per_session": 4,
                    "strengths": ["architecture", "design_negotiation", "api_compat"],
                },
                "risk_responsibility": [
                    {"threshold": 0.5, "role": "ai"},
                    {"threshold": 1.0, "role": "expert"},
                ],
                "handover_timing": {"prefer_early": 0.4, "handover_overhead_budget": 1.0},
            },
            [
                {"type": "risk_gate", "base_threshold": 0.6},
                {"type": "confidence", "floor": 0.35},
                {"type": "load_aware", "fatigue_ceiling": 0.7},
            ],
            [
                {
                    "id": "pr-501",
                    "title": "Auth service rewrite",
                    "steps": [
                        {"id": "pr-501-f0", "description": "Review: critical module", "complexity": 0.75, "risk": 0.85, "requires_expert": True},
                        {"id": "pr-501-f1", "description": "Review: supporting file", "complexity": 0.35, "risk": 0.25},
                        {"id": "pr-501-f2", "description": "Review: critical module", "complexity": 0.75, "risk": 0.85, "requires_expert": True},
                        {"id": "pr-501-f3", "description": "Review: critical module", "complexity": 0.75, "risk": 0.85, "requires_expert": True},
                    ],
                },
                {
                    "id": "pr-502",
                    "title": "Rename and refactor utilities",
                    "steps": [
                        {"id": "pr-502-f0", "description": "Review: supporting file", "complexity": 0.35, "risk": 0.25},
                        {"id": "pr-502-f1", "description": "Review: supporting file", "complexity": 0.35, "risk": 0.25},
                        {"id": "pr-502-f2", "description": "Review: supporting file", "complexity": 0.35, "risk": 0.25},
                        {"id": "pr-502-f3", "description": "Review: supporting file", "complexity": 0.35, "risk": 0.25},
                    ],
                },
            ],
        ),
    ]


@app.get("/api/presets")
def presets() -> list[dict[str, Any]]:
    return _presets()


@app.post("/api/simulate")
def simulate(req: SimulateRequest) -> dict[str, Any]:
    try:
        metaknowledge = _build_metaknowledge(req.metaknowledge)
        policies = [_build_policy(p) for p in req.policies or []]
        tasks = _build_tasks(req.tasks)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not tasks:
        raise HTTPException(status_code=422, detail="Add at least one task to the canvas first")
    if not (1 <= req.n_runs <= 200):
        raise HTTPException(status_code=422, detail="n_runs must be between 1 and 200")

    framework = HMCFramework(
        name=req.framework_name or "my-framework",
        metaknowledge=metaknowledge,
        policies=policies,
    )
    runner = SimulationRunner(framework, seed=req.seed)

    report = EvaluationReport(framework.name)
    if req.mode == "repeated":
        for task in tasks:
            for run in runner.evaluate_repeated(task, n_runs=req.n_runs).runs:
                report.runs.append(run)
        report.metadata = {"seed": req.seed, "n_runs": req.n_runs, "type": "repeated"}
    else:
        for run in runner.evaluate_tasks(tasks).runs:
            report.runs.append(run)
        report.metadata = {"seed": req.seed, "type": "tasks"}

    seci = SECIEngine(metaknowledge, learning_rate=req.learning_rate).run(report)
    updated = seci.apply(metaknowledge)

    return {
        "framework_name": framework.name,
        "metadata": report.metadata,
        "aggregated": report.aggregated(),
        "runs": [_run_to_dict(r) for r in report.runs],
        "seci": {
            "lessons": [
                {"stage": l.stage, "content": l.content, "evidence": l.evidence}
                for l in seci.lessons
            ],
            "patch": seci.patch,
            "recommendations": seci.recommendations,
        },
        "meta_after": updated.summary(),
    }


def main() -> None:
    """Run the server: python -m crusaders.gui_server [port]"""
    import sys

    import uvicorn

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
