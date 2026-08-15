import { createContext, useContext, useReducer, type ReactNode } from "react";
import type {
  Config,
  Metaknowledge,
  PolicySpec,
  Preset,
  StepSpec,
  TaskSpec,
} from "./types";

export type Selection =
  | { kind: "task"; id: string }
  | { kind: "step"; taskId: string; id: string }
  | { kind: "policy"; index: number }
  | { kind: "metaknowledge" }
  | null;

type Action =
  | { type: "LOAD_PRESET"; preset: Preset }
  | { type: "SET_FRAMEWORK_NAME"; value: string }
  | { type: "SET_METAKNOWLEDGE"; patch: Partial<Metaknowledge> }
  | { type: "ADD_TASK" }
  | { type: "REMOVE_TASK"; id: string }
  | { type: "UPDATE_TASK"; id: string; patch: Partial<TaskSpec> }
  | { type: "ADD_STEP"; taskId: string; after?: number }
  | { type: "REMOVE_STEP"; taskId: string; id: string }
  | { type: "UPDATE_STEP"; taskId: string; id: string; patch: Partial<StepSpec> }
  | { type: "MOVE_STEP"; taskId: string; from: number; to: number }
  | { type: "ADD_POLICY"; policy: PolicySpec; after?: number }
  | { type: "REMOVE_POLICY"; index: number }
  | { type: "UPDATE_POLICY"; index: number; patch: Partial<PolicySpec> }
  | { type: "MOVE_POLICY"; from: number; to: number }
  | { type: "SET_MODE"; mode: Config["mode"] }
  | { type: "SET_N_RUNS"; value: number }
  | { type: "SET_SEED"; value: number }
  | { type: "SELECT"; selection: Selection };

export function defaultConfig(): Config {
  return {
    framework_name: "My Collaboration Framework",
    metaknowledge: {
      ai_boundary: { max_complexity: 0.6, allowed_domains: ["general tasks"] },
      expert_capability: { max_steps_per_session: 6, strengths: ["judgement", "ethics"] },
      risk_responsibility: [
        { threshold: 0.4, role: "ai" },
        { threshold: 1.0, role: "expert" },
      ],
      handover_timing: { prefer_early: 0.3, handover_overhead_budget: 1.0 },
    },
    policies: [],
    tasks: [],
    mode: "tasks",
    n_runs: 1,
    seed: 3,
  };
}

function uid(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 8)}`;
}

function reducer(state: Config, action: Action): Config {
  switch (action.type) {
    case "LOAD_PRESET":
      return {
        ...state,
        framework_name: action.preset.framework_name,
        metaknowledge: structuredClone(action.preset.metaknowledge),
        policies: structuredClone(action.preset.policies),
        tasks: structuredClone(action.preset.tasks),
      };
    case "SET_FRAMEWORK_NAME":
      return { ...state, framework_name: action.value };
    case "SET_METAKNOWLEDGE":
      return {
        ...state,
        metaknowledge: { ...state.metaknowledge, ...action.patch },
      };
    case "ADD_TASK": {
      const task: TaskSpec = {
        id: uid("task"),
        title: `New Task ${state.tasks.length + 1}`,
        steps: [],
      };
      return { ...state, tasks: [...state.tasks, task] };
    }
    case "REMOVE_TASK":
      return { ...state, tasks: state.tasks.filter((t) => t.id !== action.id) };
    case "UPDATE_TASK":
      return {
        ...state,
        tasks: state.tasks.map((t) =>
          t.id === action.id ? { ...t, ...action.patch } : t
        ),
      };
    case "ADD_STEP": {
      const step: StepSpec = {
        id: uid("step"),
        description: "Untitled step",
        complexity: 0.5,
        risk: 0.3,
        requires_expert: false,
      };
      return {
        ...state,
        tasks: state.tasks.map((t) => {
          if (t.id !== action.taskId) return t;
          const idx = action.after ?? t.steps.length;
          const steps = [...t.steps];
          steps.splice(idx, 0, step);
          return { ...t, steps };
        }),
      };
    }
    case "REMOVE_STEP":
      return {
        ...state,
        tasks: state.tasks.map((t) =>
          t.id === action.taskId
            ? { ...t, steps: t.steps.filter((s) => s.id !== action.id) }
            : t
        ),
      };
    case "UPDATE_STEP":
      return {
        ...state,
        tasks: state.tasks.map((t) =>
          t.id === action.taskId
            ? {
                ...t,
                steps: t.steps.map((s) =>
                  s.id === action.id ? { ...s, ...action.patch } : s
                ),
              }
            : t
        ),
      };
    case "MOVE_STEP": {
      return {
        ...state,
        tasks: state.tasks.map((t) => {
          if (t.id !== action.taskId) return t;
          const steps = [...t.steps];
          const [moved] = steps.splice(action.from, 1);
          if (!moved) return t;
          steps.splice(action.to, 0, moved);
          return { ...t, steps };
        }),
      };
    }
    case "ADD_POLICY": {
      const policies = [...state.policies];
      policies.splice(action.after ?? policies.length, 0, action.policy);
      return { ...state, policies };
    }
    case "REMOVE_POLICY":
      return {
        ...state,
        policies: state.policies.filter((_, i) => i !== action.index),
      };
    case "UPDATE_POLICY": {
      const policies = state.policies.map((p, i) =>
        i === action.index ? { ...p, ...action.patch } : p
      );
      return { ...state, policies };
    }
    case "MOVE_POLICY": {
      const policies = [...state.policies];
      const [moved] = policies.splice(action.from, 1);
      if (!moved) return state;
      policies.splice(action.to, 0, moved);
      return { ...state, policies };
    }
    case "SET_MODE":
      return { ...state, mode: action.mode };
    case "SET_N_RUNS":
      return { ...state, n_runs: Math.max(1, Math.min(200, action.value)) };
    case "SET_SEED":
      return { ...state, seed: action.value };
    case "SELECT":
      return { ...state, ...{} };
    default:
      return state;
  }
}

interface StoreContextValue {
  config: Config;
  selection: Selection;
  dispatch: (action: Action) => void;
  select: (selection: Selection) => void;
}

const StoreContext = createContext<StoreContextValue | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [state, rawDispatch] = useReducer(reducer, undefined, defaultConfig);
  const [selection, select] = useReducer(
    (_s: Selection, sel: Selection) => sel,
    null
  );

  return (
    <StoreContext.Provider
      value={{ config: state, selection, dispatch: rawDispatch, select }}
    >
      {children}
    </StoreContext.Provider>
  );
}

export function useStore(): StoreContextValue {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used inside StoreProvider");
  return ctx;
}
