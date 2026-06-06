import { useEffect, useState } from "react";

import { useReplay } from "../lib/replayContext";

interface Props {
  onClose: () => void;
  onPlayFromStart: () => void;
  onSeek: (ms: number) => void;
}

interface Step {
  eyebrow: string;
  title: string;
  body: string;
  enter?: () => void;
}

export function Tutorial({ onClose, onPlayFromStart, onSeek }: Props) {
  const { duration } = useReplay();

  const steps: Step[] = [
    {
      eyebrow: "Briefing 01 / 06",
      title: "Welcome to the Command Center",
      body: "This is a decentralized multi-agent system defending a simulated corporate network. Five autonomous BDI agent types cooperate to detect, classify, and neutralize attacks in under a second. This tour plays a real recorded multi-segment incident.",
    },
    {
      eyebrow: "02 / 06 · Topology",
      title: "Four network segments",
      body: "On the left, each zone (Internal, Server, Public-Facing, Security Monitoring) is watched by its own Traffic Monitor, Anomaly Classifier, and Response Coordinator. Green is nominal; the border flares red under attack.",
      enter: () => onSeek(0),
    },
    {
      eyebrow: "03 / 06 · The attack",
      title: "Press play — the attack lands",
      body: "A DDoS floods Public-Facing while a lateral-movement breach spreads through Internal. Watch the Traffic Monitors raise alerts and the alert feed light up on the right.",
      enter: () => onPlayFromStart(),
    },
    {
      eyebrow: "04 / 06 · The pipeline",
      title: "Detect → classify → respond",
      body: "Messages flow TMA → ACA → RCA in the center canvas. The Anomaly Classifier scores each threat with scikit-learn; the Response Coordinator picks the least-disruptive effective action — throttling the flood to preserve availability.",
      enter: () => onSeek(duration * 0.5),
    },
    {
      eyebrow: "05 / 06 · Coalition",
      title: "Coordinated defense",
      body: "Because two segments are hit at once, the Threat Intelligence agent correlates them and forms a coalition (the dashed violet overlay). High-risk quarantines require a majority vote of the coalition before they execute.",
      enter: () => onSeek(duration * 0.8),
    },
    {
      eyebrow: "06 / 06 · Proof",
      title: "Provably within spec",
      body: "The bottom panels show live metrics against the SRS targets, and the host overhead stays under its 40% cap. Open the Validator tab to see all six stress-test scenarios pass with Social Welfare ≥ 0.80.",
      enter: () => onSeek(duration),
    },
  ];

  const [i, setI] = useState(0);

  useEffect(() => {
    steps[i].enter?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [i]);

  const step = steps[i];
  const last = i === steps.length - 1;

  return (
    <div className="tut-overlay" onClick={onClose}>
      <div className="tut-card" onClick={(e) => e.stopPropagation()}>
        <div className="tut-step">{step.eyebrow}</div>
        <h2>{step.title}</h2>
        <p>{step.body}</p>
        <div className="tut-actions">
          <div className="tut-dots">
            {steps.map((_, idx) => (
              <span key={idx} className={idx === i ? "on" : ""} />
            ))}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {i > 0 && (
              <button className="btn" onClick={() => setI(i - 1)}>
                Back
              </button>
            )}
            {!last ? (
              <button className="btn primary" onClick={() => setI(i + 1)}>
                Next
              </button>
            ) : (
              <button className="btn primary" onClick={onClose}>
                Enter Console
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
