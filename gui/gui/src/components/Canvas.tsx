import { useRef, type DragEvent } from "react";
import { useStore } from "../store";
import type { MetaInfo, PolicySpec, TaskSpec } from "../types";
import {
  IconBolt,
  IconClose,
  IconGrip,
  IconPlay,
  IconPlus,
  IconTrash,
  PolicyIcon,
} from "../icons";

type DragPayload =
  | { kind: "task" }
  | { kind: "step" }
  | { kind: "policy"; type: string }
  | { kind: "step-move"; taskId: string; from: number }
  | { kind: "policy-move"; from: number };

function readDrag(e: DragEvent): DragPayload | null {
  const raw = e.dataTransfer.getData("application/x-crusaders");
  if (!raw) return null;
  try {
    return JSON.parse(raw) as DragPayload;
  } catch {
    return null;
  }
}

export function Canvas({
  meta,
  running,
  error,
  onRun,
}: {
  meta: MetaInfo | null;
  running: boolean;
  error: string | null;
  onRun: () => void;
}) {
  const { config, dispatch, selection, select } = useStore();

  return (
    <>
      <Toolbar running={running} onRun={onRun} />

      {error && (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: 12,
            background: "rgba(251,113,133,0.1)",
            border: "1px solid rgba(251,113,133,0.35)",
            color: "var(--bad)",
            fontSize: 12.5,
          }}
        >
          {error}
        </div>
      )}

      <section className="glass" style={{ padding: 14 }}>
        <div className="sec-title" style={{ paddingTop: 0 }}>
          <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className="dot" />
            Flow · Tasks &amp; steps
          </span>
          <span>drag steps in, or tap + on a card</span>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            minHeight: 60,
          }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            const p = readDrag(e);
            if (p?.kind === "task") {
              dispatch({ type: "ADD_TASK" });
              e.stopPropagation();
            }
          }}
        >
          {config.tasks.length === 0 && (
            <div className="empty-hint">
              The canvas is empty - drag a <b>Task</b> in (or click to add), then
              <br />
              drop <b>Steps</b> into the card to build a collaboration flow.
            </div>
          )}
          {config.tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              selected={selection?.kind === "task" && selection.id === task.id}
              onSelect={() => select({ kind: "task", id: task.id })}
            />
          ))}
        </div>
        <div
          className="drop-zone"
          style={{ marginTop: 10 }}
          onDragOver={(e) => {
            e.preventDefault();
            e.currentTarget.classList.add("over");
          }}
          onDragLeave={(e) => e.currentTarget.classList.remove("over")}
          onDrop={(e) => {
            e.currentTarget.classList.remove("over");
            const p = readDrag(e);
            if (p?.kind === "task") {
              dispatch({ type: "ADD_TASK" });
              e.stopPropagation();
            }
          }}
        >
          Drop a Task here to create one
        </div>
      </section>

      <section className="glass" style={{ padding: 14 }}>
        <div className="sec-title" style={{ paddingTop: 0 }}>
          <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className="dot" />
            Collaboration rules · handover policies
          </span>
          <span>run in order; tap a card to tune</span>
        </div>

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            minHeight: 40,
          }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            const p = readDrag(e);
            if (p?.kind === "policy") {
              dispatch({
                type: "ADD_POLICY",
                policy: makePolicy(p.type, meta),
              });
              e.stopPropagation();
            }
          }}
        >
          {config.policies.length === 0 && (
            <div className="empty-hint">
              No handover policies yet - drag a <b>Policy</b> in from the left
              <br />
              to decide when control moves between AI and expert.
            </div>
          )}
          {config.policies.map((pol, i) => (
            <PolicyCard
              key={`${pol.type}-${i}`}
              policy={pol}
              index={i}
              meta={meta}
              selected={selection?.kind === "policy" && selection.index === i}
              onSelect={() => select({ kind: "policy", index: i })}
            />
          ))}
        </div>
        <div
          className="drop-zone"
          style={{ marginTop: 10 }}
          onDragOver={(e) => {
            e.preventDefault();
            e.currentTarget.classList.add("over");
          }}
          onDragLeave={(e) => e.currentTarget.classList.remove("over")}
          onDrop={(e) => {
            e.currentTarget.classList.remove("over");
            const p = readDrag(e);
            if (p?.kind === "policy") {
              dispatch({
                type: "ADD_POLICY",
                policy: makePolicy(p.type, meta),
              });
              e.stopPropagation();
            }
          }}
        >
          Drop a Policy here to stack another rule
        </div>
      </section>
    </>
  );
}

/* ------------------------------------------------------------------ */

function Toolbar({
  running,
  onRun,
}: {
  running: boolean;
  onRun: () => void;
}) {
  const { config, dispatch } = useStore();
  return (
    <div className="glass" style={{ padding: "10px 14px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", rowGap: 8 }}>
        <div style={{ display: "flex", gap: 4, padding: 3, borderRadius: 999, background: "rgba(255,255,255,0.05)", border: "1px solid var(--glass-border)" }}>
          <button
            className={`btn small ${config.mode === "tasks" ? "primary" : "ghost"}`}
            style={{ borderRadius: 999 }}
            onClick={() => dispatch({ type: "SET_MODE", mode: "tasks" })}
          >
            Single run
          </button>
          <button
            className={`btn small ${config.mode === "repeated" ? "primary" : "ghost"}`}
            style={{ borderRadius: 999 }}
            onClick={() => dispatch({ type: "SET_MODE", mode: "repeated" })}
          >
            Repeated
          </button>
        </div>
        <div className="field" style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <label htmlFor="n_runs" style={{ margin: 0 }}>
            Runs/task
          </label>
          <input
            id="n_runs"
            className="num-input"
            type="number"
            min={1}
            max={200}
            value={config.n_runs}
            onChange={(e) =>
              dispatch({ type: "SET_N_RUNS", value: Number(e.target.value) })
            }
            disabled={config.mode === "tasks"}
          />
          <label htmlFor="seed" style={{ margin: 0 }}>
            Seed
          </label>
          <input
            id="seed"
            className="num-input"
            type="number"
            value={config.seed}
            onChange={(e) =>
              dispatch({ type: "SET_SEED", value: Number(e.target.value) })
            }
          />
        </div>
        <button
          className="btn primary"
          style={{ marginLeft: "auto", borderRadius: 999, padding: "8px 20px" }}
          onClick={onRun}
          disabled={running || config.tasks.length === 0}
        >
          {running ? <span className="spin" /> : <IconPlay />}
          {running ? "Simulating…" : "Run simulation"}
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function TaskCard({
  task,
  selected,
  onSelect,
}: {
  task: TaskSpec;
  selected: boolean;
  onSelect: () => void;
}) {
  const { dispatch, selection, select } = useStore();
  const insertAt = useRef<number>(task.steps.length);
  const stepListRef = useRef<HTMLDivElement>(null);

  const nSteps = task.steps.length;
  const nExpert = task.steps.filter((s) => s.requires_expert).length;

  return (
    <div className={`glass task-card ${selected ? "selected" : ""}`}>
      <div
        className="task-head"
        onClick={onSelect}
        style={{ cursor: "pointer" }}
      >
        <span className="grip">
          <IconGrip />
        </span>
        <input
          className="t-title"
          value={task.title}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) =>
            dispatch({ type: "UPDATE_TASK", id: task.id, patch: { title: e.target.value } })
          }
        />
        <div className="task-stats">
          <span className="pill">{nSteps} steps</span>
          {nExpert > 0 && (
            <span className="pill" style={{ color: "var(--expert)" }}>
              {nExpert} expert
            </span>
          )}
          <button
            className="icon-btn"
            title="Add step"
            onClick={(e) => {
              e.stopPropagation();
              dispatch({ type: "ADD_STEP", taskId: task.id });
              select({ kind: "task", id: task.id });
            }}
          >
            <IconPlus />
          </button>
          <button
            className="icon-btn danger"
            title="Delete task"
            onClick={(e) => {
              e.stopPropagation();
              dispatch({ type: "REMOVE_TASK", id: task.id });
            }}
          >
            <IconTrash />
          </button>
        </div>
      </div>

      <div
        ref={stepListRef}
        className="step-list"
        onDragOver={(e) => {
          e.preventDefault();
          const p = readDrag(e);
          if (!p) return;
          const kids = Array.from(
            stepListRef.current?.children ?? []
          ) as HTMLElement[];
          let to = kids.length;
          for (let i = 0; i < kids.length; i++) {
            const r = kids[i].getBoundingClientRect();
            if (e.clientY < r.top + r.height / 2) {
              to = i;
              break;
            }
          }
          insertAt.current = to;
          kids.forEach((k) => {
            k.style.borderTop = "";
            k.style.borderBottom = "";
          });
          if (to === 0 && kids.length > 0) {
            kids[0].style.borderTop = "1.5px solid var(--accent)";
          } else if (to > 0) {
            kids[Math.min(to - 1, kids.length - 1)].style.borderBottom =
              "1.5px solid var(--accent)";
          }
        }}
        onDragLeave={() => {
          stepListRef.current?.childNodes.forEach((n) => {
            (n as HTMLElement).style.borderTop = "";
            (n as HTMLElement).style.borderBottom = "";
          });
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          const p = readDrag(e);
          const to = insertAt.current;
          stepListRef.current?.childNodes.forEach((n) => {
            (n as HTMLElement).style.borderTop = "";
            (n as HTMLElement).style.borderBottom = "";
          });
          if (p?.kind === "step") {
            dispatch({ type: "ADD_STEP", taskId: task.id, after: to });
          } else if (p?.kind === "step-move" && p.taskId === task.id) {
            const from = p.from;
            if (from === to || from === to - 1) return;
            dispatch({
              type: "MOVE_STEP",
              taskId: task.id,
              from,
              to: from < to ? to - 1 : to,
            });
          }
        }}
      >
        {task.steps.map((step, i) => (
          <div
            key={step.id}
            className={`step-row ${
              selection?.kind === "step" &&
              selection.taskId === task.id &&
              selection.id === step.id
                ? "selected"
                : ""
            }`}
            draggable
            onDragStart={(e) => {
              beginDragStep(e, task.id, i);
            }}
            onClick={(e) => {
              e.stopPropagation();
              select({ kind: "step", taskId: task.id, id: step.id });
            }}
          >
            <span className="grip">
              <IconGrip />
            </span>
            <span className="step-badge">{i + 1}</span>
            <span className="step-mid">
              <div className="step-desc">{step.description}</div>
              <div className="step-meta">
                <span className="mini-tag">complexity {step.complexity.toFixed(2)}</span>
                <span className={`mini-tag ${step.risk > 0.5 ? "hi" : ""}`}>
                  risk {step.risk.toFixed(2)}
                </span>
                {step.requires_expert && (
                  <span className="mini-tag expert">expert</span>
                )}
              </div>
            </span>
            <button
              className="icon-btn danger"
              title="Delete step"
              onClick={(e) => {
                e.stopPropagation();
                dispatch({ type: "REMOVE_STEP", taskId: task.id, id: step.id });
              }}
            >
              <IconTrash />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function PolicyCard({
  policy,
  index,
  meta,
  selected,
  onSelect,
}: {
  policy: PolicySpec;
  index: number;
  meta: MetaInfo | null;
  selected: boolean;
  onSelect: () => void;
}) {
  const { dispatch } = useStore();
  const def = meta?.policies.find((p) => p.type === policy.type);
  const brief =
    def?.params
      .filter((p) => policy[p.key] !== undefined)
      .map((p) => `${p.label} ${policy[p.key]}`)
      .join(" · ") ?? "";

  return (
    <div
      className={`glass-soft policy-card ${selected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <div
        className="policy-head"
        draggable
        onDragStart={(e) => {
          e.dataTransfer.setData(
            "application/x-crusaders",
            JSON.stringify({ kind: "policy-move", from: index })
          );
          e.dataTransfer.effectAllowed = "move";
        }}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          const p = readDrag(e);
          if (p?.kind === "policy-move") {
            dispatch({ type: "MOVE_POLICY", from: p.from, to: index });
          }
        }}
      >
        <span className="icon-tile">
          <PolicyIcon name={def?.icon ?? "shield"} />
        </span>
        <span className="pl-name">{def?.label ?? policy.type}</span>
        <span className="pl-order">
          rule {index + 1} · drag to reorder
        </span>
        <span
          className="icon-btn danger"
          onClick={(e) => {
            e.stopPropagation();
            dispatch({ type: "REMOVE_POLICY", index });
          }}
        >
          <IconClose width={12} height={12} />
        </span>
      </div>
      <div className="policy-brief">
        {def?.description}
        {brief && (
          <span style={{ display: "block", marginTop: 6, color: "var(--text-2)" }}>
            <IconBolt style={{ verticalAlign: -1 }} /> {brief}
          </span>
        )}
        {policy.type === "composite" && Array.isArray(policy.policies) && (
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {(policy.policies as PolicySpec[]).map((sub, si) => {
              const subDef = meta?.policies.find((p) => p.type === sub.type);
              return (
                <span
                  key={si}
                  style={{
                    fontSize: 11,
                    color: "var(--text-2)",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  <span style={{ color: "var(--accent-2)" }}>⊟</span>
                  {subDef?.label ?? sub.type}
                </span>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function makePolicy(type: string, meta: MetaInfo | null): PolicySpec {
  const def = meta?.policies.find((p) => p.type === type);
  const spec: PolicySpec = { type };
  for (const p of def?.params ?? []) spec[p.key] = p.default;
  if (type === "composite") {
    spec.majority = 0.5;
    spec.policies = [
      { type: "risk_gate", base_threshold: 0.55 },
      { type: "confidence", floor: 0.4 },
    ];
  }
  return spec;
}

function beginDragStep(e: DragEvent, taskId: string, from: number) {
  e.dataTransfer.setData(
    "application/x-crusaders",
    JSON.stringify({ kind: "step-move", taskId, from })
  );
  e.dataTransfer.effectAllowed = "move";
}
