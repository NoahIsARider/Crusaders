"""Crusaders - a scaffold for designing, running and evaluating
Human-Machine Collaboration frameworks driven by dynamic power handover.

Quick start::

    from crusaders import HMCFramework, TaskSpec, StepSpec, SimulationRunner

    class MyFramework(HMCFramework):
        def decide_handover(self, step, session):
            return HandoverDecision(Role.EXPERT if step.step.risk > 0.5 else Role.AI)

    task = TaskSpec("t1", "demo").add_step(StepSpec("s1", "do something", risk=0.8))
    report = SimulationRunner(MyFramework()).evaluate_tasks([task])
    print(report.to_markdown())
"""

from __future__ import annotations

from .adapters import AIModel, Expert, OpenAIAdapter, RuleBasedAI, SimulatedExpert
from .core.types import (
    AgentDecision,
    HandoverDirection,
    HandoverEvent,
    HandoverOutcome,
    HandoverState,
    HandoverTrigger,
    Role,
    SessionSnapshot,
    StepContext,
    StepOutcome,
    StepSpec,
    TaskOutcome,
    TaskSpec,
)
from .framework import HMCFramework, HandoverDecision
from .mediators import (
    CognitiveLoadMediator,
    DecisionTimeMediator,
    FatigueMediator,
    HandoverAccuracyMediator,
    MediatorBase,
    MediatorRegistry,
    MetricResult,
)
from .metaknowledge import OrganizationalMetaknowledge, RiskResponsibility
from .observability import EvaluationReport, RunResult, TraceRecorder
from .performance import (
    EfficiencyMetric,
    MetricSet,
    PerformanceMetric,
    QualityMetric,
    SafetyMetric,
)
from .policies import (
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
from .runner import SimulationRunner
from .seci import KnowledgeUpdate, Lesson, SECIEngine

__version__ = "0.1.0"

__all__ = [
    "AIModel",
    "AgentDecision",
    "AlwaysAI",
    "AlwaysExpert",
    "CognitiveLoadMediator",
    "CompositePolicy",
    "ConfidencePolicy",
    "DecisionTimeMediator",
    "EfficiencyMetric",
    "EvaluationReport",
    "Expert",
    "FatigueMediator",
    "HMCFramework",
    "HandoverAccuracyMediator",
    "HandoverDecision",
    "HandoverDirection",
    "HandoverEvent",
    "HandoverOutcome",
    "HandoverPolicy",
    "HandoverState",
    "HandoverTrigger",
    "KnowledgeUpdate",
    "Lesson",
    "LoadAwarePolicy",
    "MediatorBase",
    "MediatorRegistry",
    "MetricResult",
    "MetricSet",
    "OpenAIAdapter",
    "OrganizationalMetaknowledge",
    "PerformanceMetric",
    "PolicyDecision",
    "QualityMetric",
    "RiskGatePolicy",
    "RiskResponsibility",
    "Role",
    "RuleBasedAI",
    "SECIEngine",
    "SafetyMetric",
    "SessionSnapshot",
    "SessionState",
    "SimulatedExpert",
    "SimulationRunner",
    "StepContext",
    "StepOutcome",
    "StepSpec",
    "TaskOutcome",
    "TaskSpec",
    "TraceRecorder",
    "__version__",
]
