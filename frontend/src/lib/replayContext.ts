import { createContext, useContext } from "react";

import type { Beat } from "./director";
import type { DerivedState } from "./replay";
import type { ExportData } from "./types";

export type DirectorMode = "manual" | "auto";

export interface DirectorState {
  active: boolean;
  beats: Beat[];
  index: number;
  mode: DirectorMode;
  start: () => void;
  stop: () => void;
  next: () => void;
  prev: () => void;
  goto: (i: number) => void;
  setMode: (m: DirectorMode) => void;
}

export interface ReplayCtx {
  data: ExportData;
  scenarios: string[];
  scenario: number;
  selectScenario: (i: number) => void;
  duration: number;
  t: number;
  setT: (n: number) => void;
  playing: boolean;
  setPlaying: (b: boolean) => void;
  speed: number;
  setSpeed: (n: number) => void;
  derived: DerivedState;
  director: DirectorState;
}

export const ReplayContext = createContext<ReplayCtx | null>(null);

export function useReplay(): ReplayCtx {
  const ctx = useContext(ReplayContext);
  if (!ctx) throw new Error("useReplay must be used within ReplayContext");
  return ctx;
}
