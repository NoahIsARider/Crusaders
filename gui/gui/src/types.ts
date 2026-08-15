export interface PolicyParam {
  key: string;
  label: string;
  kind: "slider" | "toggle";
  min?: number;
  max?: number;
  step?: number;
  default: number | boolean;
  help?: string;
}

export interface PolicyMeta {
  type: string;
  label: string;
  icon: string;
  description: string;
  params: PolicyParam[];
  nested?: string;
}

export interface MetricMeta {
  key: string;
  label: string;
  higher_is_better: boolean;
  kind: "outcome" | "process";
}

export interface MetaInfo {
  policies: PolicyMeta[];
  metrics: MetricMeta[];
  roles: string[];
  presets: string[];
}

export interface PolicySpec {
  type: string;
  [key: string]: unknown;
}

export interface StepSpec {
  id: string;
  description: string;
  complexity: number;
  risk: number;
  requires_expert: boolean;
}

export interface TaskSpec {
  id: string;
  title: string;
  ideal_time?: number | null;
  steps: StepSpec[];
}

export interface RiskBand {
  threshold: number;
  role: "ai" | "expert" | "shared";
}

export interface Metaknowledge {
  ai_boundary: { max_complexity: number; allowed_domains: string[] };
  expert_capability: { max_steps_per_session: number; strengths: string[] };
  risk_responsibility: RiskBand[];
  handover_timing: { prefer_early: number; handover_overhead_budget: number };
}

export interface Config {
  framework_name: string;
  metaknowledge: Metaknowledge;
  policies: PolicySpec[];
  tasks: TaskSpec[];
  mode: "tasks" | "repeated";
  n_runs: number;
  seed: number;
}

export interface Preset {
  id: string;
  name: string;
  tagline: string;
  framework_name: string;
  metaknowledge: Metaknowledge;
  policies: PolicySpec[];
  tasks: TaskSpec[];
}

export interface HandoverEvent {
  timestamp: number;
  direction: "ai->expert" | "expert->ai";
  trigger: string;
  step_id: string;
  reason: string;
  duration: number;
}

export interface StepRun {
  step_id: string;
  description: string;
  complexity: number;
  risk: number;
  requires_expert: boolean;
  controller: "ai" | "expert";
  passed: boolean;
  quality_estimate: number;
  confidence: number;
  latency: number;
}

export interface RunResult {
  task: string;
  elapsed: number;
  successful: boolean;
  n_steps: number;
  passed_steps: number;
  n_handovers: number;
  mediators: Record<string, number>;
  performance: Record<string, number>;
  handover_events: HandoverEvent[];
  steps: StepRun[];
}

export interface SeciOutput {
  lessons: { stage: string; content: string; evidence: Record<string, unknown> }[];
  patch: Record<string, unknown>;
  recommendations: Record<string, number>;
}

export interface SimulateResponse {
  framework_name: string;
  metadata: { seed?: number; n_runs?: number; type?: string };
  aggregated: Record<string, number>;
  runs: RunResult[];
  seci: SeciOutput;
  meta_after: {
    version: number;
    ai_boundary: Record<string, unknown>;
    expert_capability: Record<string, unknown>;
    risk_responsibility: { threshold: number; role: string }[];
    handover_timing: Record<string, unknown>;
    n_lessons: number;
  };
}
