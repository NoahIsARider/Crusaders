import { useEffect, useState } from "react";
import { fetchMeta, fetchPresets, simulate } from "./api";
import { useStore } from "./store";
import type { MetaInfo, Preset, SimulateResponse } from "./types";
import { Header } from "./components/Header";
import { Palette } from "./components/Palette";
import { Canvas } from "./components/Canvas";
import { Inspector } from "./components/Inspector";
import { Results } from "./components/Results";

export default function App() {
  const { config } = useStore();
  const [meta, setMeta] = useState<MetaInfo | null>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [result, setResult] = useState<SimulateResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchMeta().then(setMeta).catch(() => undefined);
    fetchPresets().then(setPresets).catch(() => undefined);
  }, []);

  async function runSimulation() {
    setRunning(true);
    setError(null);
    try {
      const res = await simulate(config);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="app">
      <div className="ambient" aria-hidden />
      <Header presets={presets} />
      <div className="main">
        <div className="col col-palette">
          <Palette meta={meta} presets={presets} />
        </div>
        <div className="col col-canvas">
          <Canvas
            meta={meta}
            running={running}
            error={error}
            onRun={runSimulation}
          />
        </div>
        <div className="col col-inspector">
          <Inspector meta={meta} />
        </div>
      </div>
      {result && <Results result={result} meta={meta} onClose={() => setResult(null)} />}
    </div>
  );
}
