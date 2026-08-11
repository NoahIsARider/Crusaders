# Tutorial: build your first framework

You are a team that triages support tickets. You want the AI to handle the easy
stuff and a human to own anything risky. This tutorial builds that framework,
measures it, and improves it with the feedback loop. It takes about ten minutes.

## 1. Model the work

Every job is a `TaskSpec` made of `StepSpec`s. Each step carries two numbers that
drive everything downstream: `complexity` (how hard) and `risk` (how bad if wrong).

```python
from hmcforge import StepSpec, TaskSpec

def support_task(ticket_id, sensitive):
    return (
        TaskSpec(ticket_id, "Support ticket")
        .add_step(StepSpec("classify", "Classify the ticket", complexity=0.2, risk=0.1))
        .add_step(StepSpec("answer", "Draft the answer", complexity=0.4, risk=0.2))
        .add_step(
            StepSpec(
                "verify",
                "Verify sensitive data handling",
                complexity=0.6,
                risk=0.9,
                requires_expert=sensitive,
            )
        )
    )
```

Note `requires_expert=True`: a hard constraint. Even the most aggressive AI-only
policy cannot take that step.

## 2. Describe your organisation

Meta-knowledge is the moderator. It says how much the AI is trusted, how much a
human can take before tiring, and who owns risk at each level.

```python
from hmcforge import OrganizationalMetaknowledge, RiskResponsibility

meta = OrganizationalMetaknowledge(
    ai_boundary={"max_complexity": 0.6, "allowed_domains": ["classify", "draft"]},
    expert_capability={"max_steps_per_session": 4},
    risk_responsibility=[
        RiskResponsibility(0.4, "ai"),
        RiskResponsibility(1.0, "expert"),
    ],
    handover_timing={"handover_overhead_budget": 0.8},
)
```

The policies you pick will read these numbers, so changing one line here changes
the collaboration behaviour everywhere.

## 3. Write the handover logic

Two options. Start with composition:

```python
from hmcforge import HMCFramework
from hmcforge.policies import CompositePolicy, ConfidencePolicy, LoadAwarePolicy, RiskGatePolicy

framework = HMCFramework(
    name="ticket-adaptive",
    metaknowledge=meta,
    policies=[
        CompositePolicy(
            [
                RiskGatePolicy(base_threshold=0.5),
                ConfidencePolicy(floor=0.4),
                LoadAwarePolicy(fatigue_ceiling=0.7),
            ]
        )
    ],
)
```

Or write the rule by hand. Subclassing gives you access to `session` (fatigue,
cognitive load, step counts) and the raw `step`:

```python
from hmcforge import HMCFramework, HandoverDecision, Role

class TicketFramework(HMCFramework):
    def decide_handover(self, step, session):
        if step.step.requires_expert and session.current_controller is Role.AI:
            return HandoverDecision(Role.EXPERT, reason="sensitive step")
        if step.step.risk > 0.6 and session.current_controller is Role.AI:
            return HandoverDecision(Role.EXPERT, reason="high risk")
        if session.fatigue > 0.7 and session.current_controller is Role.EXPERT:
            return HandoverDecision(Role.AI, reason="expert needs a break")
        return HandoverDecision(session.current_controller, reason="keep")

framework = TicketFramework(name="ticket-handrolled", metaknowledge=meta)
```

Both are the same thing to the platform: one method answering *who's next*.

## 4. Run it and grade it

```python
from hmcforge import SimulationRunner

tasks = [support_task("T-1", sensitive=False), support_task("T-2", sensitive=True)]
report = SimulationRunner(framework, seed=7).evaluate_tasks(tasks)

print(report.to_markdown())
report.to_json("ticket-report.json")
```

You get mediators (fatigue, cognitive load, decision time, handover accuracy) and
performance (quality, efficiency, safety). For statistical confidence, run the same
task many times:

```python
report = SimulationRunner(framework, seed=7).evaluate_repeated(support_task("T-2", True), n_runs=50)
```

## 5. Improve it with the feedback loop

```python
from hmcforge import SECIEngine

engine = SECIEngine(meta, learning_rate=0.3)
update = engine.run(report)

for lesson in update.lessons:
    print(f"[{lesson.stage}] {lesson.content}")
print("patch:", update.patch)
print("recommendations:", update.recommendations)

meta = update.apply(meta)          # versioned copy, original untouched
framework.metaknowledge = meta     # next round is moderated by what happened
```

## 6. Put a real AI in the loop

Both actors are protocols. Swap the simulated actors for a live model:

```python
from hmcforge import OpenAIAdapter

ai = OpenAIAdapter()  # reads USER_LLM_API_KEY, USER_LLM_BASE_URL, USER_LLM_MODEL
report = SimulationRunner(framework).evaluate_tasks(tasks, ai=ai)
```

Or implement `AIModel` / `Expert` yourself — one method each.

## Next steps

- Copy one of the [built-in scenarios](scenarios.md) and modify it.
- Add a custom mediator or performance metric (see [API reference](api.md)).
- Tune `learning_rate` and watch meta-knowledge evolve across rounds.
