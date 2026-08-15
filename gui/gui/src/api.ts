import type { Config, MetaInfo, Preset, SimulateResponse } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = String(body.detail);
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export function fetchMeta(): Promise<MetaInfo> {
  return request<MetaInfo>("/api/meta");
}

export function fetchPresets(): Promise<Preset[]> {
  return request<Preset[]>("/api/presets");
}

export function simulate(config: Config): Promise<SimulateResponse> {
  return request<SimulateResponse>("/api/simulate", {
    method: "POST",
    body: JSON.stringify(config),
  });
}
