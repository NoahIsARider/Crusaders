# Crusaders

**A scaffold for designing, running and evaluating Human-Machine Collaboration
frameworks driven by dynamic power handover.**

This is the documentation index. New here? Start with the tutorial.

- [Tutorial: build your first framework](tutorial.md)
- [The model behind the platform](theory.md)
- [Architecture](architecture.md)
- [Built-in scenarios](scenarios.md)
- [API reference](api.md)

## What Crusaders is

Crusaders is not a human-machine collaboration framework. It is a **workshop** for
building them:

- You describe tasks, steps, risk and complexity.
- You define who controls each step (`HMCFramework.decide_handover`).
- The platform runs the choreography, records every handover event, measures the
  process variables (fatigue, cognitive load, decision time, handover accuracy) and
  the outcomes (quality, efficiency, safety).
- A SECI feedback loop turns the evidence into updated organisational
  meta-knowledge that moderates your next iteration.

Everything is deterministic given a seed, so experiments are reproducible, and both
actors (AI and expert) are protocols you can replace with real systems.

## Installation

```bash
pip install aicrusaders
```

Optional LLM support:

```bash
pip install "aicrusaders[llm]"
```

Development install:

```bash
git clone https://github.com/NoahIsARider/Crusaders.git
cd crusaders
pip install -e ".[dev]"
```

## 30-second demo

```python
from crusaders import SimulationRunner, SECIEngine
from crusaders.scenarios import code_review

report = SimulationRunner(code_review.framework(), seed=1).evaluate_tasks(code_review.tasks())
print(report.to_markdown())

engine = SECIEngine(code_review.default_metaknowledge())
print(engine.run(report).patch)
```

Or run the bundled CLI demo:

```bash
crusaders-demo
```
