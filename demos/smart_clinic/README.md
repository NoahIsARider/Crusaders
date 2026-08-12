# Smart Community Clinic / Family-Doctor Demo

**When does the AI diagnose on its own - and when do we hand the consultation
over to a doctor?**

A complete, runnable case study on the Crusaders framework. A community
clinic / family-doctor practice wants an AI front-desk that triages and treats
routine cases, but nobody trusts a black box to own a diagnosis. This demo
builds the handover policy that answers that question, measures it, lets it
learn from its own performance, and compares it against naive baselines.

The domain is Chinese-language (the scenario it was built for), the code and
handover reasons are English (so the logic reads the same everywhere).

## What this demo shows

| File | What it is |
|---|---|
| `clinic_cases.py` | The clinic: organisational meta-knowledge (risk bands, AI boundary, doctor session budget) and an 11-patient roster. |
| `clinic_framework.py` | The handover design: `SmartClinicFramework` (5 ordered rules) + a custom `AutonomousDiagnosisMediator` and a custom `clinic_step_evaluator`. |
| `run_demo.py` | The end-to-end run: walkthroughs, a clinic-morning simulation, the SECI learning loop, and a policy comparison. |
| `outputs/` | Generated reports (Markdown + JSON) - overwritten by every run. |

## Run it

```bash
pip install aicrusaders       # or: pip install -e ".[dev]" from repo root
cd demos/smart_clinic
python run_demo.py
```

Everything is deterministic (fixed seed), so the output is identical on every
machine - an experiment you can share and reproduce.

## The handover question, answered

The whole design lives in one method, `SmartClinicFramework.decide_handover`,
and reads the clinic's meta-knowledge instead of hard-coding thresholds:

1. **Red flags & vulnerable patients** (`requires_expert`) - children, frail
   elderly, unstable presentations. The doctor takes over. Nothing else is
   consulted.
2. **The diagnosis autonomy gate** - the AI owns low-acuity complaints
   outright; it may diagnose shared-band presentations when the picture is
   unambiguous and inside the AI complexity boundary; ambiguous or high-acuity
   presentations go to the doctor.
3. **The plan step** - prescriptions, dose changes and mental-health plans
   need a clinician; self-care advice for low-risk complaints does not.
4. **Doctor overload** - when the clinician hits their session budget or
   fatigue ceiling, low-risk work is routed back to the AI.
5. **No churn** - otherwise control stays where it is.

The 11 patients in `clinic_cases.py` are calibrated so every rule fires:

- **AI handles autonomously**: common cold, allergic rhinitis, seasonal flu.
- **AI diagnoses + doctor writes the plan**: suspected UTI, diabetes dose
  change, adolescent anxiety.
- **Doctor-led**: unexplained fatigue (ambiguous picture), pediatric fever /
  elderly dizziness / chest pain (red flags), and a 12-step comprehensive
  geriatric assessment that triggers the doctor-load rule.

## What you should look at in the output

**Walkthroughs** - three consultations printed step by step, including the
reason behind every `AI -> doctor` and `doctor -> AI` handover.

**Clinic morning** - all 11 patients scored. The aggregated report includes a
custom mediator, `ai_autonomy` (share of consultation steps the AI carried
without a clinician), added via the mediator extension point.

**SECI learning loop** - three rounds of run -> measure -> patch. In this
baseline the clinic learns its doctors are not overloaded, so the organisation
*raises* the human session budget from 6 to 9. Re-calibrate the patient panel
(e.g. more red flags) and you will watch it instead narrow the AI boundary.

**Comparison** - the same roster under four handover designs:

| framework | quality | safety | ai_autonomy | fatigue | decision time |
|---|---|---|---|---|---|
| **adaptive (this demo)** | 1.00 | 1.00 | 0.74 | 0.02 | 2.65 s |
| doctor-only | 1.00 | 0.52 | 0.00 | 0.10 | 5.77 s |
| ai-only | 0.92 | 0.83 | 1.00 | 0.00 | 1.43 s |
| generic policy stack | 1.00 | 0.71 | 0.38 | 0.04 | 4.20 s |

The adaptive clinic keeps the doctor's safety (1.00, same as doctor-only)
while automating 74% of the work - the two things a naive baseline never gets
at once.

## Extend it

- Add a patient: one `Patient(...)` row in `PATIENTS`; the consultation
  template builds the task for you.
- Add a screening step: bump `_comprehensive_assessment()`.
- Tighten or loosen autonomy: edit `RISK_BANDS` / `AI_MAX_COMPLEXITY` in
  `clinic_cases.py`, or `CONFIDENCE_FLOOR` / `LOW_RISK_GATE` in
  `clinic_framework.py`.
- Plug in a real LLM: swap the AI actor in `make_runner` for an
  `OpenAIAdapter` (needs `pip install 'aicrusaders[llm]'` and your own
  `USER_LLM_API_KEY`).

## Related

- [Crusaders README](../../README.md) - the framework this demo runs on.
- `src/crusaders/scenarios/healthcare_triage.py` - the built-in emergency
  department triage scenario (a different handover philosophy: aggressive
  human safety net, no autonomy).
