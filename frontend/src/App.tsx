import { useEffect, useMemo, useRef, useState } from "react";
import { Route, Routes } from "react-router-dom";

import { Header } from "./components/Header";
import { ReplayControls } from "./components/ReplayControls";
import { Tutorial } from "./components/Tutorial";
import rawData from "./data/replay.json";
import { deriveState } from "./lib/replay";
import { ReplayContext } from "./lib/replayContext";
import type { ExportData } from "./lib/types";
import { Dashboard } from "./pages/Dashboard";
import { Inspector } from "./pages/Inspector";
import { Validator } from "./pages/Validator";

const data = rawData as unknown as ExportData;
const duration = Math.max(data.replay.duration_ms, 1);
const segments = data.topology.segments;

export default function App() {
  const [t, setT] = useState(duration); // start fully revealed; tutorial/scrub to replay
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(2);
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const last = useRef<number | null>(null);

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
  }, [playing, speed]);

  const derived = useMemo(() => deriveState(data.replay.events, t, segments), [t]);

  const restart = () => {
    setT(0);
    setPlaying(true);
  };

  return (
    <ReplayContext.Provider
      value={{ data, duration, t, setT, playing, setPlaying, speed, setSpeed, derived }}
    >
      <div className="app">
        <Header onTutorial={() => setTutorialOpen(true)} />
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
