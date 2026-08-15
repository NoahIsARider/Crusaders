import { useStore } from "../store";
import type { Preset } from "../types";
import { IconSpark } from "../icons";

export function Header({ presets }: { presets: Preset[] }) {
  const { dispatch, config } = useStore();

  function loadPreset(preset: Preset) {
    dispatch({ type: "LOAD_PRESET", preset });
  }

  return (
    <header className="header glass" style={{ flexWrap: "wrap" }}>
      <div className="brand">
        <span className="brand-name">CRUSADERS · Studio</span>
        <span className="brand-sub">Visual human-machine collaboration studio</span>
      </div>
      <span className="pill">
        <span className="status-dot" />
        Simulation engine ready
      </span>
      <div className="header-spacer" />
      <span className="pill" style={{ maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
        Framework{" "}
        <span style={{ color: "var(--text-1)", fontWeight: 600 }}>
          {config.framework_name || "Untitled"}
        </span>
      </span>
      <span className="pill">
        Tasks <b style={{ color: "var(--text-1)" }}>{config.tasks.length}</b>
      </span>
      <span className="pill">
        Policies <b style={{ color: "var(--text-1)" }}>{config.policies.length}</b>
      </span>
      {presets.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: 6,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <IconSpark />
          {presets.map((p) => (
            <button
              key={p.id}
              className="btn small ghost"
              onClick={() => loadPreset(p)}
              title={p.tagline}
            >
              {p.name}
            </button>
          ))}
        </div>
      )}
    </header>
  );
}
