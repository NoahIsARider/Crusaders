# Built-in scenarios

Three complete, runnable case studies. Each module exports the same four things, so
you can treat them as templates:

- `default_metaknowledge()` — the organisation (moderator).
- `tasks()` — a task corpus.
- `framework()` — a ready-to-use reference framework.
- `DOMAIN` — the scenario name.

```python
from hmcforge import SimulationRunner
from hmcforge.scenarios import financial_underwriting

report = SimulationRunner(financial_underwriting.framework(), seed=3).evaluate_tasks(
    financial_underwriting.tasks()
)
print(report.aggregated())
```

## 1. Healthcare triage — `healthcare_triage`

**Philosophy: human-in-the-loop safety net.** The AI streams intake data fast;
anything above a modest risk band is pulled back by a clinician. Meta-knowledge is
deliberately conservative (narrow AI boundary, explicit risk bands).

- `SafetyNetTriageFramework` subclass: handcrafted `decide_handover`.
- Demonstrates `requires_expert` hard constraints on red-flag screening.
- Good starting point for anything safety-critical (diagnostics, compliance
  screening, incident response).

## 2. Financial underwriting — `financial_underwriting`

**Philosophy: confidence-driven delegation.** The AI does routine scoring and
document extraction; the underwriter owns judgement calls and anything the AI flags
as uncertain. Risk responsibility is mostly shared (AI recommends, human approves).

- `framework()` is built purely by composing `CompositePolicy`, `RiskGatePolicy`,
  `ConfidencePolicy`, `LoadAwarePolicy` — no subclass needed.
- Good starting point for decision-heavy back-office work.

## 3. Code review — `code_review`

**Philosophy: efficiency-driven, load-aware.** The AI does the mechanical pass over
every file; a senior engineer joins for critical files and is routed back to the AI
when their load climbs.

- Demonstrates the load-aware handover in action and how
  `expert_capability.max_steps_per_session` shapes the human's session budget.
- Good starting point for knowledge-work productivity tools.

## Comparing frameworks

Run the same scenario corpus under different frameworks and compare
`EvaluationReport.aggregated()` values. The built-in scenarios differentiate mainly
through handover accuracy and fatigue, which is exactly what the model predicts
should move first:

```python
from hmcforge import HMCFramework
from hmcforge.policies import AlwaysAI, AlwaysExpert
from hmcforge.scenarios import code_review
from hmcforge import SimulationRunner

for name, policies in [("ai-only", [AlwaysAI()]), ("expert-only", [AlwaysExpert()])]:
    fw = HMCFramework(name=name, metaknowledge=code_review.default_metaknowledge(), policies=policies)
    agg = SimulationRunner(fw, seed=3).evaluate_tasks(code_review.tasks()).aggregated()
    print(name, {k: round(v, 2) for k, v in agg.items() if k != "decision_time"})
```

Expect: the AI-only baseline is cheap (efficiency ~1.0) but fails hard on critical
files (low quality and safety); the expert-only baseline maximises quality but
loads the human (high cognitive load, and fatigue that would compound over a longer
session).
