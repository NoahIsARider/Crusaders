import type { MetaInfo, RunResult, SimulateResponse } from "../types";
import { IconClose, IconGauge, IconSpark } from "../icons";

export function Results({
  result,
  meta,
  onClose,
}: {
  result: SimulateResponse;
  meta: MetaInfo | null;
  onClose: () => void;
}) {
  const metricDefs = meta?.metrics ?? [];

  function status(key: string, value: number): "good" | "bad" | "neutral" {
    const def = metricDefs.find((m) => m.key === key);
    const higher = def?.higher_is_better ?? true;
    if (higher) return value >= 0.7 ? "good" : value <= 0.45 ? "bad" : "neutral";
    return value <= 0.3 ? "good" : value >= 0.6 ? "bad" : "neutral";
  }

  return (
    <div className="overlay">
      <div className="results-panel glass">
        <div className="results-head">
          <span
            style={{
              width: 9,
              height: 9,
              borderRadius: 3,
              background: "var(--accent-grad)",
            }}
          />
          <span className="results-title">Simulation report · {result.framework_name}</span>
          <span className="pill">
            seed {result.metadata.seed ?? "-"}
            {result.metadata.n_runs ? ` · ${result.metadata.n_runs} runs/task` : ""}
          </span>
          <span className="pill">{result.runs.length} task runs</span>
          <button className="btn ghost small" style={{ marginLeft: "auto" }} onClick={onClose}>
            <IconClose /> Close
          </button>
        </div>

        <div className="results-scroll">
          <div className="metric-grid">
            {Object.entries(result.aggregated).map(([key, value]) => {
              const def = metricDefs.find((m) => m.key === key);
              const st = status(key, value);
              return (
                <div key={key} className={`metric-card ${st}`}>
                  <span className="mc-key">{key}</span>
                  <span className="mc-val">{value.toFixed(3)}</span>
                  <span className="mc-label">{def?.label ?? key}</span>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{ width: `${Math.min(100, value * 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="sub-sec">Per-task run details</div>
          <div className="run-grid">
            {result.runs.map((run, i) => (
              <RunCard key={i} run={run} index={i} metricDefs={metricDefs} />
            ))}
          </div>

          <div className="sub-sec">SECI organisational feedback</div>
          <SeciSection result={result} />
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function RunCard({
  run,
  index,
  metricDefs,
}: {
  run: RunResult;
  index: number;
  metricDefs: { key: string; label: string }[];
}) {
  const dirLabel = (dir: string) =>
    dir === "ai->expert" ? "AI → Expert" : "Expert → AI";
  const triggerLabel: Record<string, string> = {
    policy: "policy",
    expert_callback: "expert callback",
    ai_escalation: "AI escalation",
    scheduled: "scheduled",
    exception: "exception",
  };

  return (
    <div className="run-card glass-soft">
      <div className="rc-head">
        <span className="rc-task">
          {index + 1}. {run.task}
        </span>
        <span className={`pill ${run.successful ? "" : ""}`}>
          {run.passed_steps}/{run.n_steps} steps passed
        </span>
      </div>
      <div className="rc-pair">
        <span>Elapsed</span>
        <span>{run.elapsed.toFixed(2)}s</span>
      </div>
      <div className="rc-pair">
        <span>Handovers</span>
        <span>{run.n_handovers}</span>
      </div>
      {Object.entries(run.performance).map(([k, v]) => {
        const def = metricDefs.find((m) => m.key === k);
        return (
          <div className="rc-pair" key={k}>
            <span>{def?.label ?? k}</span>
            <span>{v.toFixed(3)}</span>
          </div>
        );
      })}

      {run.handover_events.length > 0 && (
        <div className="timeline">
          {run.handover_events.map((ev, i) => (
            <div
              key={i}
              className={`tl-item ${ev.direction === "ai->expert" ? "to-expert" : ""}`}
            >
              <span className="tl-dir">{dirLabel(ev.direction)}</span>
              <span className="tl-step">{ev.step_id}</span>
              <span className="tl-reason">
                {triggerLabel[ev.trigger] ?? ev.trigger}
              </span>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {run.steps.map((s) => (
          <div className="step-run" key={s.step_id}>
            <span className={s.controller === "ai" ? "ctl-ai" : "ctl-expert"}>
              {s.controller === "ai" ? "AI" : "Expert"}
            </span>
            <span
              style={{
                flex: 1,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                color: "var(--text-2)",
              }}
            >
              {s.description}
            </span>
            <span className={`sr-pass ${s.passed ? "pass" : "fail"}`}>
              {s.passed ? "Pass" : "Fail"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function SeciSection({ result }: { result: SimulateResponse }) {
  const stageLabel: Record<string, string> = {
    socialization: "Socialise",
    externalization: "Externalise",
    combination: "Combine",
    internalization: "Internalise",
  };

  const recommendations = result.seci.recommendations;
  const patch = result.seci.patch as Record<string, unknown>;
  const patchEntries: [string, string][] = Object.entries(patch).flatMap(
    ([, v]) =>
      Object.entries(v as Record<string, unknown>).map(
        ([pk, pv]) => [pk, String(pv)] as [string, string]
      )
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {result.seci.lessons.length > 0 && (
        <div className="seci-card glass-soft">
          <span
            style={{
              display: "flex",
              gap: 7,
              alignItems: "center",
              fontSize: 11,
              fontWeight: 650,
              letterSpacing: "0.1em",
              color: "var(--text-2)",
            }}
          >
            <IconSpark /> Distilled lessons
          </span>
          {result.seci.lessons.map((l, i) => (
            <div className="lesson-row" key={i}>
              <span className="lr-stage">{stageLabel[l.stage] ?? l.stage}</span>
              <span className="lr-content">{l.content}</span>
            </div>
          ))}
        </div>
      )}

      {patchEntries.length > 0 && (
        <div className="seci-card glass-soft">
          <span
            style={{
              display: "flex",
              gap: 7,
              alignItems: "center",
              fontSize: 11,
              fontWeight: 650,
              letterSpacing: "0.1em",
              color: "var(--text-2)",
            }}
          >
            <IconGauge /> Auto-updated org meta-knowledge
          </span>
          <div className="kv-grid">
            {patchEntries.map(([k, v]) => (
              <div className="kv-cell" key={k}>
                <div className="kv-k">{k}</div>
                <div className="kv-v">{String(v)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.keys(recommendations).length > 0 && (
        <div className="seci-card glass-soft">
          <span
            style={{
              display: "flex",
              gap: 7,
              alignItems: "center",
              fontSize: 11,
              fontWeight: 650,
              letterSpacing: "0.1em",
              color: "var(--text-2)",
            }}
          >
            Next-round policy suggestions
          </span>
          <div className="kv-grid">
            {Object.entries(recommendations).map(([k, v]) => (
              <div className="kv-cell" key={k}>
                <div className="kv-k">{k}</div>
                <div className="kv-v">{Number(v).toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.seci.lessons.length === 0 &&
        patchEntries.length === 0 &&
        Object.keys(recommendations).length === 0 && (
          <div className="seci-card glass-soft">
            <span className="help">
              This round looks healthy - the SECI engine produced no updates. Try
              more extreme settings to see a change.
            </span>
          </div>
        )}
    </div>
  );
}
