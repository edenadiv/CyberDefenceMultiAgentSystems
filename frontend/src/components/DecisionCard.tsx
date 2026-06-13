/* Decision pop-over: a readout of the REAL numbers behind the active beat's decision —
   classifier confidence/novelty/features, the per-voter quarantine vote, or the auction
   bids. Driven by the director's current beat (Phase 1 enriched these into the data). */
import { useReplay } from "../lib/replayContext";
import type { CdmasEvent } from "../lib/types";

function num(v: unknown, d = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

function ClassifyCard({ e }: { e: CdmasEvent }) {
  const dt = e.decision_trace;
  const features = dt?.features ?? [];
  const names = dt?.feature_names ?? [];
  const max = Math.max(1e-9, ...features.map((f) => Math.abs(f)));
  const sev = num(e.payload?.severity);
  return (
    <div className="decision-card" data-kind="classify">
      <div className="decision-head">
        <span className="decision-agent">ACA</span> hybrid classifier
      </div>
      <div className="decision-verdict">
        {String(e.payload?.attack_type ?? "THREAT")}
        <span className={`decision-chip ${sev >= 0.7 ? "hot" : "warm"}`}>
          {String(e.payload?.classification ?? "")}
        </span>
      </div>
      <div className="decision-metrics">
        <div>
          <label>confidence</label>
          <b>{num(dt?.confidence).toFixed(2)}</b>
        </div>
        <div>
          <label>novelty</label>
          <b>{num(dt?.novelty).toFixed(2)}</b>
        </div>
        <div>
          <label>severity</label>
          <b>{sev.toFixed(2)}</b>
        </div>
      </div>
      {features.length > 0 && (
        <div className="decision-spark" title="9-D packet feature vector">
          {features.map((f, i) => (
            <span
              key={i}
              className="spark-bar"
              style={{ height: `${Math.max(6, (Math.abs(f) / max) * 100)}%` }}
              title={`${names[i] ?? "f" + i}: ${f}`}
            />
          ))}
        </div>
      )}
      <div className="decision-foot">RandomForest + nearest-neighbour novelty · 9-D features</div>
    </div>
  );
}

function VoteCard({ e }: { e: CdmasEvent }) {
  const votes = e.decision_trace?.votes ?? {};
  const approved = !!e.payload?.approved;
  return (
    <div className="decision-card" data-kind="vote">
      <div className="decision-head">
        <span className="decision-agent">RCA</span> quarantine vote
      </div>
      <div className={`decision-verdict ${approved ? "ok" : "bad"}`}>
        {approved ? "QUARANTINE APPROVED" : "REJECTED → BLOCK"}
      </div>
      <div className="decision-voters">
        {Object.entries(votes).map(([voter, decision]) => (
          <div key={voter} className="voter-row">
            <span className={`voter-mark ${decision === "ACCEPT" ? "yes" : "no"}`}>
              {decision === "ACCEPT" ? "✓" : "✗"}
            </span>
            <span className="voter-id">{voter}</span>
            <span className="voter-dec">{String(decision)}</span>
          </div>
        ))}
      </div>
      <div className="decision-foot">
        {num(e.payload?.accept_count)}/{num(e.payload?.member_count)} accept · majority rule
      </div>
    </div>
  );
}

function AuctionCard({ e }: { e: CdmasEvent }) {
  const bids = (e.payload?.bids ?? {}) as Record<string, number>;
  const granted = new Set((e.payload?.granted as string[] | undefined) ?? []);
  const entries = Object.entries(bids).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1e-9, ...entries.map(([, v]) => v));
  return (
    <div className="decision-card" data-kind="auction">
      <div className="decision-head">
        <span className="decision-agent">RAA</span> sealed-bid auction
      </div>
      <div className="decision-bids">
        {entries.map(([bidder, value]) => (
          <div key={bidder} className="bid-row">
            <span className="bid-id">{bidder.replace(/^RCA:/, "")}</span>
            <span className="bid-bar-track">
              <span
                className={`bid-bar ${granted.has(bidder) ? "won" : "lost"}`}
                style={{ width: `${(value / max) * 100}%` }}
              />
            </span>
            <span className="bid-val">{value.toFixed(2)}</span>
            <span className={`bid-tag ${granted.has(bidder) ? "won" : "lost"}`}>
              {granted.has(bidder) ? "GRANTED" : "DENIED"}
            </span>
          </div>
        ))}
      </div>
      <div className="decision-foot">
        {granted.size}/{num(e.payload?.slots)} slots · highest severity wins
      </div>
    </div>
  );
}

export function DecisionCard() {
  const { director } = useReplay();
  const beat = director.beats[director.index];
  if (!beat?.event) return null;
  if (beat.kind === "classify") return <ClassifyCard e={beat.event} />;
  if (beat.kind === "vote") return <VoteCard e={beat.event} />;
  if (beat.kind === "auction") return <AuctionCard e={beat.event} />;
  return null;
}
