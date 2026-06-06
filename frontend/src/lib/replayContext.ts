import { createContext, useContext } from "react";

import type { DerivedState } from "./replay";
import type { ExportData } from "./types";

export interface ReplayCtx {
  data: ExportData;
  duration: number;
  t: number;
  setT: (n: number) => void;
  playing: boolean;
  setPlaying: (b: boolean) => void;
  speed: number;
  setSpeed: (n: number) => void;
  derived: DerivedState;
}

export const ReplayContext = createContext<ReplayCtx | null>(null);

export function useReplay(): ReplayCtx {
  const ctx = useContext(ReplayContext);
  if (!ctx) throw new Error("useReplay must be used within ReplayContext");
  return ctx;
}
