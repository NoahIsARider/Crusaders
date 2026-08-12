# Framework comparison - smart clinic morning

Same 11-patient roster, same seed, four handover designs.

| framework | quality | efficiency | safety | fatigue | handover_accuracy | ai_autonomy | decision_time (s) |
|---|---|---|---|---|---|---|---|
| adaptive (this demo) | 1.000 | 0.953 | 1.000 | 0.020 | 0.970 | 0.739 | 2.65 |
| doctor-only | 1.000 | 0.968 | 0.520 | 0.099 | 0.333 | 0.000 | 5.77 |
| ai-only | 0.923 | 1.000 | 0.826 | 0.000 | 0.897 | 1.000 | 1.43 |
| generic policy stack | 1.000 | 0.956 | 0.711 | 0.043 | 0.712 | 0.379 | 4.20 |

Read the numbers, then run the demo yourself: `python run_demo.py`.
