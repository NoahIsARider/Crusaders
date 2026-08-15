import { useState, type CSSProperties, type ReactNode } from "react";
import { useStore } from "../store";
import type { MetaInfo, PolicySpec } from "../types";
import { IconGauge, IconPlus, IconTrash, PolicyIcon } from "../icons";

export function Inspector({ meta }: { meta: MetaInfo | null }) {
  const { config, selection, select } = useStore();
  const [subTab, setSubTab] = useState<"meta" | "run">("meta");

  let body: ReactNode;

  if (selection?.kind === "task") {
    const task = config.tasks.find((t) => t.id === selection.id);
    body = task ? <TaskForm taskId={task.id} /> : <EmptyNote />;
  } else if (selection?.kind === "step") {
    const task = config.tasks.find((t) => t.id === selection.taskId);
    const step = task?.steps.find((s) => s.id === selection.id);
    body = step ? (
      <StepForm taskId={selection.taskId} stepId={selection.id} />
    ) : (
      <EmptyNote />
    );
  } else if (selection?.kind === "policy") {
    body = <PolicyForm index={selection.index} meta={meta} />;
  } else {
    body = <MetaForm />;
  }

  return (
    <div className="inspector-scroll">
      <div
        style={{
          display: "flex",
          gap: 4,
          padding: 3,
          borderRadius: 999,
          background: "rgba(255,255,255,0.05)",
          border: "1px solid var(--glass-border)",
        }}
      >
        <button
          className={`btn small ${subTab === "meta" ? "primary" : "ghost"}`}
          onClick={() => {
            setSubTab("meta");
            select({ kind: "metaknowledge" });
          }}
        >
          Org meta-knowledge
        </button>
        <button
          className={`btn small ${subTab === "run" ? "primary" : "ghost"}`}
          onClick={() => setSubTab("run")}
        >
          Run settings
        </button>
      </div>

      {subTab === "run" ? <RunForm /> : body}
    </div>
  );
}

function EmptyNote() {
  return (
    <div className="empty-hint">
      Tap a <b>Task / Step / Policy</b> on the canvas
      <br />
      to edit its properties here.
      <br />
      <br />
      Use <b>Org meta-knowledge</b> to configure
      <br />
      the AI boundary &amp; expert capability.
    </div>
  );
}

/* ---------------- shared field components ---------------- */

function SliderField({
  label,
  value,
  min,
  max,
  step,
  help,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  help?: string;
  onChange: (v: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;
  return (
    <div className="field">
      <label>{label}</label>
      <div className="slider-row">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          style={{ "--fill": `${pct}%` } as CSSProperties}
        />
        <span className="slider-val">{value.toFixed(2)}</span>
      </div>
      {help && <span className="help">{help}</span>}
    </div>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      <input
        className="num-input"
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

function TextField({
  label,
  value,
  help,
  onChange,
}: {
  label: string;
  value: string;
  help?: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="field">
      <label>{label}</label>
      <input
        className="text-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      {help && <span className="help">{help}</span>}
    </div>
  );
}

function ToggleRow({
  label,
  help,
  on,
  onChange,
}: {
  label: string;
  help?: string;
  on: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="toggle-row">
      <div>
        <div className="tr-label">{label}</div>
        {help && <div className="tr-help">{help}</div>}
      </div>
      <div className={`switch ${on ? "on" : ""}`} onClick={() => onChange(!on)} />
    </div>
  );
}

function Section({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="glass-soft" style={{ padding: 13 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
          flexWrap: "wrap",
          marginBottom: 11,
        }}
      >
        <span
          style={{
            fontSize: 11,
            fontWeight: 650,
            letterSpacing: "0.1em",
            color: "var(--text-2)",
          }}
        >
          {title}
        </span>
        {action}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
        {children}
      </div>
    </div>
  );
}

/* ---------------- task form ---------------- */

function TaskForm({ taskId }: { taskId: string }) {
  const { config, dispatch } = useStore();
  const task = config.tasks.find((t) => t.id === taskId);
  if (!task) return <EmptyNote />;
  return (
    <>
      <Section
        title="Task properties"
        action={
          <button
            className="icon-btn danger"
            onClick={() => dispatch({ type: "REMOVE_TASK", id: taskId })}
          >
            <IconTrash />
          </button>
        }
      >
        <TextField
          label="Task title"
          value={task.title}
          onChange={(v) =>
            dispatch({ type: "UPDATE_TASK", id: taskId, patch: { title: v } })
          }
        />
        <NumberField
          label="Ideal time (s, optional)"
          value={task.ideal_time ?? 0}
          min={0}
          max={600}
          step={0.5}
          onChange={(v) =>
            dispatch({
              type: "UPDATE_TASK",
              id: taskId,
              patch: { ideal_time: v > 0 ? v : null },
            })
          }
        />
        <div className="help">
          {task.steps.length} steps, of which{" "}
          {task.steps.filter((s) => s.requires_expert).length} require the expert.
        </div>
      </Section>
      <Section title="Flow preview">
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          {task.steps.length === 0 && (
            <span className="help">No steps yet. Drop one in or tap + to add.</span>
          )}
          {task.steps.map((s, i) => (
            <span key={s.id} style={{ fontSize: 11.5, color: "var(--text-2)" }}>
              {i + 1}. {s.description}{" "}
              {s.requires_expert && (
                <span style={{ color: "var(--expert)" }}>· expert</span>
              )}
            </span>
          ))}
        </div>
      </Section>
    </>
  );
}

/* ---------------- step form ---------------- */

function StepForm({ taskId, stepId }: { taskId: string; stepId: string }) {
  const { config, dispatch } = useStore();
  const task = config.tasks.find((t) => t.id === taskId);
  const step = task?.steps.find((s) => s.id === stepId);
  if (!step) return <EmptyNote />;
  return (
    <>
      <Section
        title="Step properties"
        action={
          <button
            className="icon-btn danger"
            onClick={() =>
              dispatch({ type: "REMOVE_STEP", taskId, id: stepId })
            }
          >
            <IconTrash />
          </button>
        }
      >
        <TextField
          label="Step description"
          value={step.description}
          onChange={(v) =>
            dispatch({
              type: "UPDATE_STEP",
              taskId,
              id: stepId,
              patch: { description: v },
            })
          }
        />
        <SliderField
          label="Complexity"
          value={step.complexity}
          min={0}
          max={1}
          step={0.05}
          help="How hard this step is. The higher it is, the less reliable the AI gets."
          onChange={(v) =>
            dispatch({
              type: "UPDATE_STEP",
              taskId,
              id: stepId,
              patch: { complexity: v },
            })
          }
        />
        <SliderField
          label="Risk"
          value={step.risk}
          min={0}
          max={1}
          step={0.05}
          help="Severity if mishandled. High-risk steps should trigger a handover policy."
          onChange={(v) =>
            dispatch({
              type: "UPDATE_STEP",
              taskId,
              id: stepId,
              patch: { risk: v },
            })
          }
        />
        <ToggleRow
          label="Must be handled by an expert"
          help="Hard constraint - no policy can delegate this to the AI."
          on={step.requires_expert}
          onChange={(v) =>
            dispatch({
              type: "UPDATE_STEP",
              taskId,
              id: stepId,
              patch: { requires_expert: v },
            })
          }
        />
      </Section>
    </>
  );
}

/* ---------------- policy form ---------------- */

function PolicyForm({ index, meta }: { index: number; meta: MetaInfo | null }) {
  const { config, dispatch } = useStore();
  const [subIdx, setSubIdx] = useState<number | null>(null);
  const policy = config.policies[index];
  if (!policy) return <EmptyNote />;
  const def = meta?.policies.find((p) => p.type === policy.type);

  const children = (policy.policies ?? []) as PolicySpec[];
  const subDef = subIdx !== null ? meta?.policies.find((p) => p.type === children[subIdx]?.type) : null;

  return (
    <>
      <Section
        title={def?.label ?? policy.type}
        action={
          <button
            className="icon-btn danger"
            onClick={() => dispatch({ type: "REMOVE_POLICY", index })}
          >
            <IconTrash />
          </button>
        }
      >
        <div className="help" style={{ paddingBottom: 2 }}>
          {def?.description}
        </div>
        {(def?.params ?? []).map((p) =>
          p.kind === "slider" ? (
            <SliderField
              key={p.key}
              label={p.label}
              value={Number(policy[p.key] ?? p.default)}
              min={p.min ?? 0}
              max={p.max ?? 1}
              step={p.step ?? 0.05}
              help={p.help}
              onChange={(v) =>
                dispatch({
                  type: "UPDATE_POLICY",
                  index,
                  patch: { [p.key]: v },
                })
              }
            />
          ) : (
            <ToggleRow
              key={p.key}
              label={p.label}
              help={p.help}
              on={Boolean(policy[p.key] ?? p.default)}
              onChange={(v) =>
                dispatch({
                  type: "UPDATE_POLICY",
                  index,
                  patch: { [p.key]: v },
                })
              }
            />
          )
        )}
      </Section>

      {policy.type === "composite" && (
        <Section
          title="Sub-policies · voting"
          action={
            <button
              className="btn small ghost"
              onClick={() =>
                dispatch({
                  type: "UPDATE_POLICY",
                  index,
                  patch: {
                    policies: [
                      ...children,
                      { type: "risk_gate", base_threshold: 0.5 },
                    ],
                  },
                })
              }
            >
              <IconPlus /> Add
            </button>
          }
        >
          {children.map((sub, i) => {
            const sd = meta?.policies.find((p) => p.type === sub.type);
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "7px 9px",
                  borderRadius: 9,
                  cursor: "pointer",
                  background:
                    subIdx === i ? "rgba(167,139,250,0.1)" : "rgba(255,255,255,0.03)",
                  border:
                    subIdx === i
                      ? "1px solid rgba(167,139,250,0.4)"
                      : "1px solid rgba(255,255,255,0.07)",
                }}
                onClick={() => setSubIdx(i)}
              >
                <span style={{ color: "var(--accent-2)", display: "grid", placeItems: "center" }}>
                  <PolicyIcon name={sd?.icon ?? "shield"} size={13} />
                </span>
                <span style={{ flex: 1, fontSize: 12, color: "var(--text-1)" }}>
                  {sd?.label ?? sub.type}
                </span>
                <button
                  className="icon-btn danger"
                  onClick={(e) => {
                    e.stopPropagation();
                    const next = children.filter((_, ci) => ci !== i);
                    dispatch({
                      type: "UPDATE_POLICY",
                      index,
                      patch: { policies: next },
                    });
                    setSubIdx(null);
                  }}
                >
                  <IconCloseSmall />
                </button>
              </div>
            );
          })}

          {subIdx !== null && subDef && (
            <div
              style={{
                padding: 11,
                borderRadius: 10,
                background: "rgba(255,255,255,0.035)",
                border: "1px solid rgba(255,255,255,0.07)",
                display: "flex",
                flexDirection: "column",
                gap: 9,
              }}
            >
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  color: "var(--accent-2)",
                  display: "flex",
                  gap: 6,
                  alignItems: "center",
                }}
              >
                <IconGauge width={12} height={12} /> {subDef.label}
              </span>
              {subDef.params.map((p) => (
                <SliderField
                  key={p.key}
                  label={p.label}
                  value={Number(children[subIdx][p.key] ?? p.default)}
                  min={p.min ?? 0}
                  max={p.max ?? 1}
                  step={p.step ?? 0.05}
                  onChange={(v) => {
                    const next = children.map((c, ci) =>
                      ci === subIdx ? { ...c, [p.key]: v } : c
                    );
                    dispatch({
                      type: "UPDATE_POLICY",
                      index,
                      patch: { policies: next },
                    });
                  }}
                />
              ))}
            </div>
          )}
        </Section>
      )}
    </>
  );
}

function IconCloseSmall() {
  return (
    <svg viewBox="0 0 24 24" width="12" height="12">
      <path
        d="M5 5l14 14M19 5L5 19"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

/* ---------------- meta-knowledge form ---------------- */

function MetaForm() {
  const { config, dispatch } = useStore();
  const mk = config.metaknowledge;

  return (
    <>
      <Section title="AI boundary">
        <SliderField
          label="Max complexity the AI may handle"
          value={mk.ai_boundary.max_complexity}
          min={0}
          max={1}
          step={0.05}
          help="How much the organisation trusts the AI. Higher means it hands over later."
          onChange={(v) =>
            dispatch({
              type: "SET_METAKNOWLEDGE",
              patch: {
                ai_boundary: { ...mk.ai_boundary, max_complexity: v },
              },
            })
          }
        />
        <TextField
          label="Allowed domains (comma separated)"
          value={mk.ai_boundary.allowed_domains.join(", ")}
          onChange={(v) =>
            dispatch({
              type: "SET_METAKNOWLEDGE",
              patch: {
                ai_boundary: {
                  ...mk.ai_boundary,
                  allowed_domains: v
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                },
              },
            })
          }
        />
      </Section>

      <Section title="Expert capability">
        <NumberField
          label="Max steps per session"
          value={mk.expert_capability.max_steps_per_session}
          min={1}
          max={30}
          onChange={(v) =>
            dispatch({
              type: "SET_METAKNOWLEDGE",
              patch: {
                expert_capability: {
                  ...mk.expert_capability,
                  max_steps_per_session: v,
                },
              },
            })
          }
        />
        <TextField
          label="Expert strengths (comma separated)"
          value={mk.expert_capability.strengths.join(", ")}
          onChange={(v) =>
            dispatch({
              type: "SET_METAKNOWLEDGE",
              patch: {
                expert_capability: {
                  ...mk.expert_capability,
                  strengths: v
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                },
              },
            })
          }
        />
      </Section>

      <Section
        title="Risk responsibility bands"
        action={
          <button
            className="btn small ghost"
            onClick={() =>
              dispatch({
                type: "SET_METAKNOWLEDGE",
                patch: {
                  risk_responsibility: [
                    ...mk.risk_responsibility,
                    { threshold: 1.0, role: "expert" },
                  ],
                },
              })
            }
          >
            <IconPlus /> Add
          </button>
        }
      >
        {mk.risk_responsibility.map((band, i) => (
          <div
            key={i}
            style={{
              padding: 9,
              borderRadius: 10,
              background: "rgba(255,255,255,0.03)",
              border: "1px solid rgba(255,255,255,0.07)",
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 11, color: "var(--text-2)" }}>
                risk ≤ {band.threshold.toFixed(2)}
              </span>
              <select
                className="text-input"
                style={{ width: "auto", marginLeft: "auto", padding: "4px 8px" }}
                value={band.role}
                onChange={(e) =>
                  dispatch({
                    type: "SET_METAKNOWLEDGE",
                    patch: {
                      risk_responsibility: mk.risk_responsibility.map((b, bi) =>
                        bi === i
                          ? { ...b, role: e.target.value as typeof b.role }
                          : b
                      ),
                    },
                  })
                }
              >
                <option value="ai">AI responsible</option>
                <option value="shared">Shared</option>
                <option value="expert">Expert responsible</option>
              </select>
              {mk.risk_responsibility.length > 1 && (
                <button
                  className="icon-btn danger"
                  onClick={() =>
                    dispatch({
                      type: "SET_METAKNOWLEDGE",
                      patch: {
                        risk_responsibility: mk.risk_responsibility.filter(
                          (_, bi) => bi !== i
                        ),
                      },
                    })
                  }
                >
                  <IconTrash />
                </button>
              )}
            </div>
            <SliderField
              label=""
              value={band.threshold}
              min={0}
              max={1}
              step={0.05}
              onChange={(v) =>
                dispatch({
                  type: "SET_METAKNOWLEDGE",
                  patch: {
                    risk_responsibility: mk.risk_responsibility.map((b, bi) =>
                      bi === i ? { ...b, threshold: v } : b
                    ),
                  },
                })
              }
            />
          </div>
        ))}
        <div className="help">
          Bands split the risk range top to bottom, deciding who answers for
          each risk level.
        </div>
      </Section>

      <Section title="Handover timing">
        <SliderField
          label="Prefer early handover"
          value={mk.handover_timing.prefer_early}
          min={0}
          max={1}
          step={0.05}
          help="Higher means control is handed over sooner."
          onChange={(v) =>
            dispatch({
              type: "SET_METAKNOWLEDGE",
              patch: {
                handover_timing: { ...mk.handover_timing, prefer_early: v },
              },
            })
          }
        />
        <NumberField
          label="Handover overhead budget (s)"
          value={mk.handover_timing.handover_overhead_budget}
          min={0}
          max={20}
          step={0.1}
          onChange={(v) =>
            dispatch({
              type: "SET_METAKNOWLEDGE",
              patch: {
                handover_timing: {
                  ...mk.handover_timing,
                  handover_overhead_budget: v,
                },
              },
            })
          }
        />
      </Section>
    </>
  );
}

/* ---------------- run settings ---------------- */

function RunForm() {
  const { config, dispatch } = useStore();
  return (
    <Section title="Run settings">
      <div className="help" style={{ paddingBottom: 2 }}>
        Each "Run simulation" drives the framework with the current config and
        returns an evaluation report plus SECI organisational knowledge.
      </div>
      <div className="toggle-row">
        <div>
          <div className="tr-label">Repeated simulation</div>
          <div className="tr-help">Run every task many times to average out noise</div>
        </div>
        <div
          className={`switch ${config.mode === "repeated" ? "on" : ""}`}
          onClick={() =>
            dispatch({
              type: "SET_MODE",
              mode: config.mode === "repeated" ? "tasks" : "repeated",
            })
          }
        />
      </div>
      <NumberField
        label="Runs per task"
        value={config.n_runs}
        min={1}
        max={200}
        onChange={(v) => dispatch({ type: "SET_N_RUNS", value: v })}
      />
      <NumberField
        label="Random seed"
        value={config.seed}
        onChange={(v) => dispatch({ type: "SET_SEED", value: v })}
      />
      <div className="help">
        The same config and seed always give identical results, so experiments
        are reproducible.
      </div>
    </Section>
  );
}
