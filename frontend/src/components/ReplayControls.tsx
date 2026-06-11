import type { CSSProperties } from "react";

import { shortScenarioName } from "../lib/replay";
import { useReplay } from "../lib/replayContext";

const SPEEDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

export function ReplayControls() {
  const {
    scenarios,
    scenario,
    selectScenario,
    t,
    setT,
    duration,
    playing,
    setPlaying,
    speed,
    setSpeed,
  } = useReplay();
  const pct = Math.min(100, (t / duration) * 100);

  const onScenario = (i: number) => {
    if (i === scenario) {
      if (t >= duration) setT(0);
      setPlaying(!playing);
    } else {
      selectScenario(i);
    }
  };

  return (
    <div style={{ padding: "0 22px 18px" }}>
      <div className="scenario-bar">
        {scenarios.map((name, i) => (
          <button
            key={name}
            className={`btn${i === scenario ? " primary" : ""}`}
            title={name}
            aria-pressed={i === scenario}
            onClick={() => onScenario(i)}
          >
            {i === scenario && playing ? "❚❚" : "▶"} <span className="scn-num">S{i + 1}</span>
            {shortScenarioName(name)}
          </button>
        ))}
      </div>
      <div className="replay">
        <button className="btn" onClick={() => { setPlaying(false); setT(0); }}>
          ⏮ Restart
        </button>
        <span className="clock mono">
          {(t / 1000).toFixed(2)}s / {(duration / 1000).toFixed(2)}s
        </span>
        <input
          className="scrub"
          type="range"
          min={0}
          max={duration}
          value={t}
          style={{ "--pct": `${pct}%` } as CSSProperties}
          onChange={(e) => {
            setPlaying(false);
            setT(Number(e.target.value));
          }}
        />
        <div className="speeds">
          {SPEEDS.map((s) => (
            <button
              key={s}
              className={s === speed ? "active" : ""}
              onClick={() => setSpeed(s)}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
