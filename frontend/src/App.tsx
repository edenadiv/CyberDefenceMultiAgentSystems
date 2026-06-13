import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Route, Routes } from "react-router-dom";

import { Backdrop } from "./components/Backdrop";
import { Director } from "./components/Director";
import { Header } from "./components/Header";
import { ReplayControls } from "./components/ReplayControls";
import rawData from "./data/replay.json";
import { type BeatKind, deriveBeats } from "./lib/director";
import { liveDerived, liveMetrics } from "./lib/liveStore";
import { deriveState } from "./lib/replay";
import { ReplayContext } from "./lib/replayContext";
import type { DirectorMode, ViewMode } from "./lib/replayContext";
import type { ExportBundle, ExportData } from "./lib/types";
import { useLiveConnection } from "./lib/useLiveConnection";
import { Dashboard } from "./pages/Dashboard";
import { Inspector } from "./pages/Inspector";
import { Validator } from "./pages/Validator";

const bundle = rawData as unknown as ExportBundle;
const scenarios = bundle.replays.map((r) => r.scenario);
// The director narrates the multi-segment incident, so it is the default/hero view.
const DEFAULT_SCENARIO = Math.max(
  0,
  bundle.replays.findIndex((r) => r.scenario.includes("Multi-Segment")),
);

// Hand-authored narration for the hero scenario's framing beats; the rest are data-driven.
const HERO_CAPTIONS: Partial<Record<BeatKind, string>> = {
  intro: "War room online — five BDI agent types stand guard over four network segments.",
  outro: "Incident closed in well under a second. Every performance target met.",
};

const HOLD_MS = 2400; // dwell on each beat before auto-advancing

export default function App() {
  const [scenario, setScenario] = useState(DEFAULT_SCENARIO);
  // start fully revealed; the director/scrub rewinds to play.
  const [t, setT] = useState(() => Math.max(bundle.replays[DEFAULT_SCENARIO].duration_ms, 1));
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [viewMode, setViewMode] = useState<ViewMode>("replay");
  const liveEnabled = viewMode === "live";
  const liveConn = useLiveConnection(liveEnabled);
  const last = useRef<number | null>(null);

  const [directorActive, setDirectorActive] = useState(false);
  const [directorIndex, setDirectorIndex] = useState(0);
  const [directorMode, setDirectorMode] = useState<DirectorMode>("manual");

  const replay = bundle.replays[scenario];
  const duration = Math.max(replay.duration_ms, 1);

  const beats = useMemo(
    () => deriveBeats(replay, scenario === DEFAULT_SCENARIO ? HERO_CAPTIONS : undefined),
    [replay, scenario],
  );

  // Mirror refs so the stable callbacks/effects below always read fresh values.
  const beatsRef = useRef(beats);
  const indexRef = useRef(directorIndex);
  const modeRef = useRef(directorMode);
  const activeRef = useRef(directorActive);
  beatsRef.current = beats;
  indexRef.current = directorIndex;
  modeRef.current = directorMode;
  activeRef.current = directorActive;

  const dwellRef = useRef<number | null>(null);
  const advancedRef = useRef(false); // guards one auto-advance schedule per beat

  const clearDwell = () => {
    if (dwellRef.current != null) {
      clearTimeout(dwellRef.current);
      dwellRef.current = null;
    }
  };

  // Seek the clock to a beat: manual holds on the decision; auto plays the run-up.
  const startBeat = useCallback((i: number, mode: DirectorMode) => {
    const b = beatsRef.current[i];
    if (!b) return;
    advancedRef.current = false;
    if (mode === "auto") {
      last.current = null;
      setT(b.windowMs[0]);
      setPlaying(true);
    } else {
      setPlaying(false);
      setT(b.atMs);
    }
  }, []);

  const next = useCallback(() => {
    const ni = Math.min(indexRef.current + 1, beatsRef.current.length - 1);
    setDirectorIndex(ni);
    startBeat(ni, modeRef.current);
  }, [startBeat]);

  const prev = useCallback(() => {
    const pi = Math.max(0, indexRef.current - 1);
    setDirectorIndex(pi);
    setPlaying(false);
    setT(beatsRef.current[pi]?.atMs ?? 0);
    advancedRef.current = false;
  }, []);

  const goto = useCallback(
    (i: number) => {
      const ci = Math.max(0, Math.min(i, beatsRef.current.length - 1));
      setDirectorIndex(ci);
      startBeat(ci, modeRef.current);
    },
    [startBeat],
  );

  const setMode = useCallback(
    (m: DirectorMode) => {
      clearDwell();
      setDirectorMode(m);
      startBeat(indexRef.current, m);
    },
    [startBeat],
  );

  const start = useCallback(() => {
    clearDwell();
    setDirectorMode("manual");
    setDirectorIndex(0);
    setDirectorActive(true);
    setPlaying(false);
    setT(0); // intro beat sits at t=0; narrates whichever scenario is selected
    advancedRef.current = false;
  }, []);

  const stop = useCallback(() => {
    clearDwell();
    setDirectorActive(false);
    setPlaying(false);
  }, []);

  // Single rAF owner: advances the clock while playing (director or free playback).
  useEffect(() => {
    if (!playing) {
      last.current = null;
      return;
    }
    let raf = 0;
    const tick = (now: number) => {
      if (last.current != null) {
        const dt = (now - last.current) * speed;
        setT((prev) => {
          const nextT = prev + dt;
          if (nextT >= duration) {
            setPlaying(false);
            return duration;
          }
          return nextT;
        });
      }
      last.current = now;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, speed, duration]);

  // Auto mode: when playback reaches the active beat, pause, dwell, then advance.
  useEffect(() => {
    if (!directorActive || directorMode !== "auto" || !playing) return;
    const target = beats[directorIndex]?.atMs ?? duration;
    if (t >= target - 0.01 && !advancedRef.current) {
      advancedRef.current = true;
      setPlaying(false);
      dwellRef.current = window.setTimeout(() => {
        if (indexRef.current < beatsRef.current.length - 1) next();
      }, HOLD_MS);
    }
  }, [t, playing, directorActive, directorMode, directorIndex, beats, duration, next]);

  // Keyboard transport while the director is on stage.
  useEffect(() => {
    if (!directorActive) return;
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === " " || e.key === "ArrowRight") {
        e.preventDefault();
        next();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        prev();
      } else if (e.key === "Escape") {
        stop();
      } else if (e.key === "a" || e.key === "A") {
        setMode(modeRef.current === "auto" ? "manual" : "auto");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [directorActive, next, prev, stop, setMode]);

  // Keep the director index sane if the scenario changes underneath it.
  useEffect(() => {
    if (activeRef.current) setDirectorIndex(0);
  }, [scenario]);

  useEffect(() => () => clearDwell(), []);

  const replayData: ExportData = useMemo(
    () => ({ topology: replay.topology, replay, validation: bundle.validation }),
    [replay],
  );
  const replayDerived = useMemo(
    () => deriveState(replay.events, t, replay.topology.segments),
    [replay, t],
  );

  // Live mode: build the same ExportData/DerivedState shape from the live store.
  const liveState = liveConn.state;
  const liveT = Math.max(liveState.lastTs, 1);
  const liveData: ExportData = useMemo(
    () => ({
      topology: liveState.topology,
      replay: {
        scenario: "LIVE",
        duration_ms: liveT,
        topology: liveState.topology,
        events: liveState.events,
        metrics: liveMetrics(liveState),
        packets: [],
      },
      validation: bundle.validation,
    }),
    [liveState, liveT],
  );
  const liveDerivedState = useMemo(() => liveDerived(liveState), [liveState]);

  // Narration is replay-only — leave the director when entering live mode.
  useEffect(() => {
    if (liveEnabled) stop();
  }, [liveEnabled, stop]);

  const data = liveEnabled ? liveData : replayData;
  const derived = liveEnabled ? liveDerivedState : replayDerived;
  const ctxT = liveEnabled ? liveT : t;
  const ctxDuration = liveEnabled ? liveT : duration;
  const ctxPlaying = liveEnabled ? !liveState.sim.paused : playing;

  const selectScenario = (i: number) => {
    setScenario(i);
    setT(0);
    if (activeRef.current) {
      // While stepping: re-narrate the newly chosen scenario from its first beat.
      setDirectorIndex(0);
      setDirectorMode("manual");
      setPlaying(false);
      advancedRef.current = false;
    } else {
      setPlaying(true);
    }
  };

  return (
    <ReplayContext.Provider
      value={{
        data,
        scenarios,
        scenario,
        selectScenario,
        duration: ctxDuration,
        t: ctxT,
        setT,
        playing: ctxPlaying,
        setPlaying,
        speed,
        setSpeed,
        derived,
        director: {
          active: directorActive,
          beats,
          index: directorIndex,
          mode: directorMode,
          start,
          stop,
          next,
          prev,
          goto,
          setMode,
        },
        viewMode,
        setViewMode,
        live: {
          connected: liveConn.connected,
          conn: liveState.conn,
          sim: liveState.sim,
          segments: liveState.topology.segments,
          sendDos: liveConn.sendDos,
          sendLegal: liveConn.sendLegal,
          setRunMode: liveConn.setRunMode,
          next: liveConn.next,
        },
      }}
    >
      <div className="app">
        <Backdrop />
        <Header onStepThrough={start} />
        <div className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/inspector" element={<Inspector />} />
            <Route path="/validator" element={<Validator />} />
          </Routes>
        </div>
        <Routes>
          <Route path="/validator" element={<div />} />
          <Route path="*" element={<ReplayControls />} />
        </Routes>
        {directorActive && <Director />}
      </div>
    </ReplayContext.Provider>
  );
}
