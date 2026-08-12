# CONTRIBUTING.md

**This project is explicitly looking for collaborators.** Crusaders is a young
project (born August 2026) with a sharp idea and a small surface — which means
every contribution moves the needle. If you work on human-AI collaboration,
human factors, ML systems, or just build things with agents and feel the
"who is in control here?" pain every day: read on.

---

## 1. Honest state of the project (known limitations)

We do not paper over the gaps. These are the current weaknesses, in order of
how much they limit the project:

1. **Everything is simulated.** All actors (`RuleBasedAI`, `SimulatedExpert`)
   are deterministic stand-ins with hand-crafted confidence/quality functions.
   Every number in a report is an *output of the framework's own assumptions*,
   not empirical evidence. The framework is a **design sandbox** today, not a
   measurement instrument — until a real case study validates (or refutes) it.
2. **The learning loop is simple.** `SECIEngine` currently distils aggregate
   statistics into parametric threshold patches (session limits, AI boundary,
   handover budget). It demonstrates the mechanism; it is not yet a serious
   learner. Claims like "the organisation learns" should be read accordingly.
3. **No trust / complacency / skill-decay modelling.** Human-factors research
   says the things that actually break human-AI teams are trust miscalibration
   (algorithm aversion & appreciation), automation complacency, and
   out-of-the-loop skill degradation. Crusaders models workload and fatigue but
   none of these. A framework that cannot tell you when collaboration is
   *worse* than either side alone is incomplete.
4. **Single-seed determinism.** Reproducible on every machine — great for
   demos, fragile for conclusions. There is no multi-seed variance, no
   confidence intervals, no significance testing.
5. **Naming friction.** Repo `Crusaders` / PyPI package `aicrusaders` /
   import `crusaders`. Three names for one thing hurts discoverability. A
   consolidation pass is wanted (but needs care: PyPI name is taken).
6. **Young engineering surface.** No CI, no coverage tracking, one author,
   no adoption signals yet. The code is clean and typed and 99 tests pass —
   but the safety net needs widening, not replacing.

---

## 2. Roadmap (prioritised)

### P0 — turn demo into evidence (the highest-value work in the project)

- [ ] **Real case study**: run a scenario with a real LLM (`OpenAIAdapter`)
      *and* real human experts (even 3–5 people), compare observed handovers /
      workload / outcomes against the simulator's predictions. Confirm or
      refute the model. This single piece of work makes Crusaders a research
      artifact instead of a prototype.
- [ ] **Cite the theory**: `docs/theory.md` currently invokes the literature
      (Sheridan & Verplank; Parasuraman; Kaber & Endsley; Nonaka; L2D line)
      without references. A proper reference list gives the project academic
      standing and is a small, high-leverage task.

### P1 — deepen the model

- [ ] Live human-in-the-loop driver: a wait-for-operator expert adapter so a
      framework can be piloted against a real person in real time.
- [ ] Trust / complacency / skill-decay mediators (with literature-grounded
      dynamics) — see limitation #3.
- [ ] Statistical helpers: multi-seed runs, variance reporting, significance
      tests for framework A/B comparisons.

### P2 — polish the surface

- [ ] A/B comparison runner as a built-in utility (currently demo-level).
- [ ] Chart exports for mediator time-series (matplotlib/plotly, no hard dep).
- [ ] CI (GitHub Actions: pytest + coverage) and a coverage badge.
- [ ] Naming consolidation or at least a documented name map.
- [ ] More scenarios from real domains: customer support escalation, radiology
      screening, autonomous vehicle intervention, loan underwriting appeals.

---

## 3. How to contribute

No contribution is too small: issues, typos in docs, a new scenario, a test,
a benchmark, a case study, a critique.

### Getting started

```bash
git clone https://github.com/NoahIsARider/Crusaders.git
cd Crusaders
pip install -e ".[dev]"
pytest                          # 99 tests, should be green
```

### Run the demo (fastest way to understand the project)

```bash
cd demos/smart_clinic
python run_demo.py
```

### Good first contributions

- Add a new scenario under `src/crusaders/scenarios/` (healthcare_triage,
  financial_underwriting and code_review are the existing patterns).
- Write the reference list for `docs/theory.md` (P0).
- Add multi-seed / variance reporting to `SimulationRunner` (P1).
- Report a real use case where you needed "who should be in control of this
  step?" answered — even a write-up of the problem is valuable data.
- Run a real-LLM variant of the smart clinic demo and post the diff between
  simulated and real handover behaviour.

### Guidelines

- Keep everything deterministic unless a change *requires* randomness
  (and then: seed it).
- Type hints + docstrings on public API, matching existing style.
- Tests for every new policy / mediator / engine behaviour.
- English for docs and code (the demo domain content may stay bilingual).
- Apache-2.0, so anything you add stays open.

### Communication

- Open an issue before large changes; small PRs are welcome directly.
- Discussion happens in issues and PRs (no external chat yet — if the project
  grows, we will add one and link it here).

---

> The question Crusaders answers — *when does the AI decide, and when do we
> hand over to a human?* — is going to be asked inside every organisation that
> deploys agents. Help us build the measuring tape for it.
