import type { CSSProperties } from "react";

import { useReplay } from "../lib/replayContext";

const SPEEDS = [1, 2, 4, 8];

export function ReplayControls() {
  const { t, setT, duration, playing, setPlaying, speed, setSpeed } = useReplay();
  const pct = Math.min(100, (t / duration) * 100);

  return (
    <div style={{ padding: "0 22px 18px" }}>
      <div className="replay">
        <button
          className="btn primary"
          onClick={() => {
            if (t >= duration) setT(0);
            setPlaying(!playing);
          }}
        >
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
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
