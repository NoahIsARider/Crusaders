# API reference

This is the complete public surface. Everything else is internal.

## Top-level imports

```python
from hmcforge import (
    HMCFramework, HandoverDecision, Role,
    OrganizationalMetaknowledge, RiskResponsibility,
    SimulationRunner, SECIEngine, KnowledgeUpdate,
    StepSpec, TaskSpec, HandoverEvent, TaskOutcome,
    # policies
    RiskGatePolicy, ConfidencePolicy, LoadAwarePolicy,
    CompositePolicy, AlwaysAI, AlwaysExpert, HandoverPolicy,
    # actors
    RuleBasedAI, SimulatedExpert, OpenAIAdapter, AIModel, Expert,
    # measurement
    FatigueMediator, CognitiveLoadMediator, DecisionTimeMediator,
    HandoverAccuracyMediator, MediatorBase, MetricResult,
    QualityMetric, EfficiencyMetric, SafetyMetric, PerformanceMetric,
    EvaluationReport, TraceRecorder,
)
```

## Domain types

### `StepSpec(id, description, complexity=0.5, risk=0.0, requires_expert=False)`
A unit of work. `complexity` and `risk` are clamped to [0, 1] (out-of-range values
raise `ValueError`). `requires_expert` is a hard constraint.

### `TaskSpec(id, title, steps=None, ideal_time=None)`
`add_step(spec)` builds fluently; `total_risk` sums step risk. `ideal_time` (seconds)
is optional and used by the efficiency metric.

### `Role` enum
`Role.AI`, `Role.EXPERT`. `Role.counterpart` gives the other role.

### `HandoverEvent(timestamp, direction, trigger, step_id, reason, ...)`
A recorded power handover. `direction` is `HandoverDirection.AI_TO_EXPERT` or
`EXPERT_TO_AI`; `trigger` is one of `POLICY`, `EXPERT_CALLBACK`, `AI_ESCALATION`,
`SCHEDULED`, `EXCEPTION`.

### `AgentDecision(role, step_id, action, content, confidence, quality_estimate, latency)`
What an actor produces for a step. `quality_estimate` in [0,1] is used by the
default step evaluator and by the quality metric.

### `TaskOutcome`
Result of one run. Fields: `task`, `step_outcomes`, `events`, `elapsed`
(simulated), `expert_active_seconds`, `ai_active_seconds`, `successful`,
`metadata`. Helpers: `n_steps`, `passed_steps`, `n_handovers`, `last_event()`.

### `StepOutcome` / `SessionSnapshot`
Per-step result including the session state snapshot (fatigue, cognitive load,
active seconds, step counts) at that moment.

## Meta-knowledge

### `OrganizationalMetaknowledge(ai_boundary, expert_capability, risk_responsibility, handover_timing, lessons)`
- `responsibility_for(risk) -> str` — role ("ai" / "expert" / "shared") for a risk level.
- `max_ai_complexity(default=0.7)`, `expert_session_limit(default=6)`,
  `handover_overhead_budget(default=5.0)` — convenience accessors.
- `update_from(patch)` — merge an update, bump `version` (returns self).
- `clone()` — independent copy (experiments never mutate shared state).
- `summary()` — dict snapshot.

### `RiskResponsibility(threshold, role)`
A band: responsibility for risks up to `threshold` belongs to `role`.

## Frameworks

### `HMCFramework(name, metaknowledge=None, policies=None, handover_overhead=None, step_evaluator=None)`
The base class. Instantiate directly with policies, or subclass and override:

```python
def decide_handover(self, step: StepContext, session: SessionState) -> HandoverDecision: ...
```

Other hooks: `before_step`, `after_step`. `add_observer(callback)` subscribes to
handover events. `run(task, ai=None, expert=None, clock=None) -> TaskOutcome`.

### `HandoverDecision(controller, trigger=POLICY, reason="")`
The verdict for a step: who takes control and why.

## Policies

All policies subclass `HandoverPolicy` and implement
`decide(step, session) -> PolicyDecision`. They are bound to meta-knowledge by the
framework, so `self.meta` is always available.

| Policy | Behaviour |
|---|---|
| `RiskGatePolicy(base_threshold=0.5)` | Expert takes over when `risk > base_threshold * ai_boundary.max_complexity`. |
| `ConfidencePolicy(floor=0.4)` | Expert steps in when AI confidence drops below `floor`. |
| `LoadAwarePolicy(fatigue_ceiling=0.8)` | Hands back to the AI when fatigue exceeds the ceiling or the session limit is reached. |
| `AlwaysAI` / `AlwaysExpert` | Baselines / ablations. |
| `CompositePolicy(policies, majority=0.5)` | Hands over when >= `majority` of sub-policies vote for the other role. |

### `SessionState`
Runtime ledger passed to policies and actors: `current_controller`, `fatigue`,
`cognitive_load`, `expert_steps`, `ai_steps`, `expert_active_seconds`,
`ai_active_seconds`, `overhead_seconds`, consecutive-step counters.

## Actors

### `RuleBasedAI(base_latency=1.2, max_complexity_skill=1.0)`
Deterministic; quality and confidence degrade with complexity.

### `SimulatedExpert(accuracy=0.9, latency=6.0, fatigue_penalty=0.3, fatigue_growth=0.08, name=...)`
Quality drops as `session.fatigue` grows. Good for modelling humans.

### `OpenAIAdapter(api_key=None, base_url=None, model=None, ...)`
LLM-backed AI reading `USER_LLM_API_KEY` / `USER_LLM_BASE_URL` /
`USER_LLM_MODEL` from the environment. Requires `pip install "hmcforge[llm]"`.

### `AIModel` / `Expert` protocols
One method each: `act(step, session) -> AgentDecision`. Implement either to plug in
your own systems.

## Mediators and performance metrics

Both produce `MetricResult(key, value, label, higher_is_better, detail, series)`.

### Built-in mediators
- `FatigueMediator` — mean human fatigue (lower better).
- `CognitiveLoadMediator` — mean cognitive load (lower better).
- `DecisionTimeMediator` — mean per-step decision latency (lower better).
- `HandoverAccuracyMediator` — fraction of steps handled by the role the
  responsibility map assigns, minus a churn penalty.

### Built-in performance metrics
- `QualityMetric` — pass rate (value), with mean quality in `detail`.
- `EfficiencyMetric(ideal_time=None)` — `ideal/elapsed`, capped at 1.0.
- `SafetyMetric` — risk-weighted fraction of load handled by the accountable role.

### Custom metric
```python
from hmcforge import MediatorBase, MetricResult

class TrustMediator(MediatorBase):
    key = "trust"
    label = "Human trust"
    higher_is_better = True

    def compute(self, outcome):
        values = [o.decision.metadata.get("trust", 0.5) for o in outcome.step_outcomes]
        return MetricResult("trust", sum(values) / len(values), self.label, True, series=values)
```

## Runner and reports

### `SimulationRunner(framework, mediators=None, metrics=None, seed=None)`
- `evaluate_tasks(tasks, ai=None, expert=None) -> EvaluationReport`
- `evaluate_repeated(task, n_runs=20, ai=None, expert=None) -> EvaluationReport`

### `EvaluationReport`
- `aggregated() -> dict[str, float]` — mean of every measured key.
- `to_dict()`, `to_json(path=None)`, `to_markdown(path=None)`.

### `TraceRecorder`
`attach(framework)` subscribes to events; `record_outcome(outcome)`;
`export() -> dict`; `to_json(path=None)`.

## SECI feedback

### `SECIEngine(metaknowledge=None, learning_rate=0.2)`
`run(report) -> KnowledgeUpdate`. Override `socialize`, `externalize`, `combine`,
`internalize` for your own knowledge rules.

### `KnowledgeUpdate(lessons, patch, recommendations)`
`apply(metaknowledge)` returns a versioned copy with patch and lessons applied.

### `Lesson(stage, content, evidence)`
A single codified knowledge item.

## Determinism

All randomness flows through `SimulationRunner.seed`. Two runners with the same
seed and identical actors produce identical reports. The default `clock` is
`perf_counter` for event timestamps; pass `clock` to `framework.run` for fully
deterministic time.
