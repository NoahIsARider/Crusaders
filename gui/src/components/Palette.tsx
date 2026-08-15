import type { DragEvent } from "react";
import { useStore } from "../store";
import type { MetaInfo, PolicySpec, Preset } from "../types";
import { IconStep, IconTask, PolicyIcon } from "../icons";

function beginDrag(e: DragEvent, payload: Record<string, unknown>) {
  e.dataTransfer.setData("application/x-crusaders", JSON.stringify(payload));
  e.dataTransfer.effectAllowed = "copy";
}

export function Palette({
  meta,
  presets,
}: {
  meta: MetaInfo | null;
  presets: Preset[];
}) {
  const { dispatch, select } = useStore();

  return (
    <>
      <section>
        <div className="sec-title">
          <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className="dot" />
            Palette
          </span>
          <span>drag to add</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div
            className="drag-item"
            draggable
            onDragStart={(e) => beginDrag(e, { kind: "task" })}
            onClick={() => dispatch({ type: "ADD_TASK" })}
          >
            <span className="icon-tile">
              <IconTask width={16} height={16} />
            </span>
            <div className="di-body">
              <div className="di-label">Task</div>
              <div className="di-desc">A job made of ordered steps</div>
            </div>
          </div>
          <div
            className="drag-item"
            draggable
            onDragStart={(e) => beginDrag(e, { kind: "step" })}
          >
            <span className="icon-tile">
              <IconStep width={16} height={16} />
            </span>
            <div className="di-body">
              <div className="di-label">Step</div>
              <div className="di-desc">Drop into a task card to chain a flow</div>
            </div>
          </div>
        </div>
      </section>

      <section>
        <div className="sec-title">
          <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className="dot" />
            Handover policies
          </span>
          <span>drag into rules</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {(meta?.policies ?? []).map((p) => (
            <div
              key={p.type}
              className="drag-item"
              draggable
              onDragStart={(e) =>
                beginDrag(e, { kind: "policy", type: p.type })
              }
              onClick={() =>
                dispatch({
                  type: "ADD_POLICY",
                  policy: defaultsFor(p.type, p.params),
                })
              }
              title={p.description}
            >
              <span className="icon-tile">
                <PolicyIcon name={p.icon} size={16} />
              </span>
              <div className="di-body">
                <div className="di-label">{p.label}</div>
                <div className="di-desc">{p.description}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="sec-title">
          <span style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className="dot" />
            Built-in scenarios
          </span>
          <span>one-click load</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {presets.map((p) => (
            <div
              key={p.id}
              className="preset-item"
              onClick={() => {
                dispatch({ type: "LOAD_PRESET", preset: p });
                select({ kind: "metaknowledge" });
              }}
            >
              <div className="pi-name">{p.name}</div>
              <div className="pi-tag">{p.tagline}</div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function defaultsFor(
  type: string,
  params: { key: string; default: number | boolean }[]
): PolicySpec {
  const spec: PolicySpec = { type };
  for (const p of params) spec[p.key] = p.default;
  return spec;
}
