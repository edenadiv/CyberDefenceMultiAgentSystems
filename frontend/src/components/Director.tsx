/* Director overlay: the cinematic narration layer that floats over the live dashboard.
   A step ribbon up top and a lower-third caption card that walk the scenario's beats.
   The dashboard stays visible behind it — the audience watches the real canvas react. */
import { useReplay } from "../lib/replayContext";
import { DecisionCard } from "./DecisionCard";

export function Director() {
  const { director } = useReplay();
  const { beats, index, mode } = director;
  const beat = beats[index];
  if (!beat) return null;

  const total = beats.length;
  const atStart = index === 0;
  const atEnd = index === total - 1;

  return (
    <div className="director" aria-live="polite">
      <div className="director-ribbon">
        <span className={`director-kind kind-${beat.kind}`}>{beat.kind}</span>
        <span className="director-ribbon-caption">{beat.caption}</span>
        <span className="director-step">
          step {index + 1}/{total}
        </span>
      </div>

      <DecisionCard />

      <div className="director-card">
        <div className="director-card-body">
          <div className="director-eyebrow">
            <span className={`director-mode ${mode}`}>
              {mode === "auto" ? "● AUTO" : "❚❚ MANUAL"}
            </span>
            scene {index + 1} of {total}
          </div>
          <div className="director-caption">{beat.caption}</div>
          {beat.sub && <div className="director-sub">{beat.sub}</div>}
        </div>

        <div className="director-controls">
          <button className="btn" onClick={director.prev} disabled={atStart}>
            ◀ Prev
          </button>
          <button
            className="btn"
            onClick={() => director.setMode(mode === "auto" ? "manual" : "auto")}
          >
            {mode === "auto" ? "❚❚ Pause auto" : "▶ Auto-play"}
          </button>
          {!atEnd ? (
            <button className="btn primary" onClick={director.next}>
              Next ▶
            </button>
          ) : (
            <button className="btn primary" onClick={director.stop}>
              Finish ▶
            </button>
          )}
          <button className="btn director-exit" onClick={director.stop} title="Exit director (Esc)">
            ✕
          </button>
        </div>
      </div>

      <div className="director-hint">Space / → next · ← back · A auto/manual · Esc exit</div>
    </div>
  );
}
