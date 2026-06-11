import { useEffect, useMemo, useRef, useState } from "react";
import { Route, Routes } from "react-router-dom";

import { Header } from "./components/Header";
import { ReplayControls } from "./components/ReplayControls";
import { Tutorial } from "./components/Tutorial";
import rawData from "./data/replay.json";
import { deriveState } from "./lib/replay";
import { ReplayContext } from "./lib/replayContext";
import type { ExportBundle, ExportData } from "./lib/types";
import { Dashboard } from "./pages/Dashboard";
import { Inspector } from "./pages/Inspector";
import { Validator } from "./pages/Validator";

const bundle = rawData as unknown as ExportBundle;
const scenarios = bundle.replays.map((r) => r.scenario);
// The guided tour narrates the multi-segment incident, so it is the default view.
const DEFAULT_SCENARIO = Math.max(
  0,
  bundle.replays.findIndex((r) => r.scenario.includes("Multi-Segment")),
);

export default function App() {
  const [scenario, setScenario] = useState(DEFAULT_SCENARIO);
  // start fully revealed; tutorial/scrub to replay
  const [t, setT] = useState(() => Math.max(bundle.replays[DEFAULT_SCENARIO].duration_ms, 1));
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const last = useRef<number | null>(null);

  const replay = bundle.replays[scenario];
  const duration = Math.max(replay.duration_ms, 1);

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
          const next = prev + dt;
          if (next >= duration) {
            setPlaying(false);
            return duration;
          }
          return next;
        });
      }
      last.current = now;
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, speed, duration]);

  const data: ExportData = useMemo(
    () => ({ topology: replay.topology, replay, validation: bundle.validation }),
    [replay],
  );
  const derived = useMemo(
    () => deriveState(replay.events, t, replay.topology.segments),
    [replay, t],
  );

  const selectScenario = (i: number) => {
    setScenario(i);
    setT(0);
    setPlaying(true);
  };

  const restart = () => selectScenario(DEFAULT_SCENARIO);

  // The tour's narration and seek points assume the default recording.
  const openTutorial = () => {
    setScenario(DEFAULT_SCENARIO);
    setPlaying(false);
    setT(Math.max(bundle.replays[DEFAULT_SCENARIO].duration_ms, 1));
    setTutorialOpen(true);
  };

  return (
    <ReplayContext.Provider
      value={{
        data,
        scenarios,
        scenario,
        selectScenario,
        duration,
        t,
        setT,
        playing,
        setPlaying,
        speed,
        setSpeed,
        derived,
      }}
    >
      <div className="app">
        <Header onTutorial={openTutorial} />
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
        {tutorialOpen && (
          <Tutorial
            onClose={() => setTutorialOpen(false)}
            onPlayFromStart={restart}
            onSeek={(ms) => {
              setPlaying(false);
              setT(ms);
            }}
          />
        )}
      </div>
    </ReplayContext.Provider>
  );
}
