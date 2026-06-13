/* Shared geometry for the message-flow canvas and topology map.
   One source of truth for node coordinates so the director (camera), the packet
   layer (sprite paths), and the decision cards (anchors) all agree. */

export interface Pt {
  x: number;
  y: number;
  color: string;
}

export interface ViewBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** The full message-flow SVG canvas (MessageFlow `viewBox`). */
export const MESSAGE_CANVAS: ViewBox = { x: 0, y: 0, w: 620, h: 380 };

/** Agent / entity node centers on the message-flow canvas. */
export const NODES: Record<string, Pt> = {
  "ATK-DDOS": { x: 90, y: 90, color: "var(--red)" },
  // shares the DDoS slot: no recording pairs them, and absent attackers aren't drawn
  "ATK-ZD": { x: 90, y: 90, color: "var(--red)" },
  "ATK-LAT": { x: 90, y: 250, color: "var(--red)" },
  CLIENTS: { x: 90, y: 170, color: "var(--cyan)" },
  NETWORK: { x: 280, y: 170, color: "var(--amber)" },
  TMA: { x: 450, y: 60, color: "var(--primary)" },
  ACA: { x: 520, y: 130, color: "var(--primary)" },
  RCA: { x: 520, y: 210, color: "var(--primary)" },
  TIA: { x: 450, y: 280, color: "var(--violet)" },
  RAA: { x: 390, y: 340, color: "var(--primary)" },
};

export const NODE_LABELS: Record<string, string> = {
  "ATK-DDOS": "ATK-DDOS",
  "ATK-ZD": "ATK-ZDAY",
  "ATK-LAT": "ATK-LAT",
  CLIENTS: "LEGIT-CLIENTS",
  NETWORK: "NETWORK",
};

export const KIND_COLOR: Record<string, string> = {
  attack: "var(--red)",
  normal: "var(--cyan)",
  allow: "var(--green)",
  alert: "var(--cyan)",
  report: "var(--green)",
  coalition: "var(--violet)",
  correlate: "var(--violet)",
  vote: "var(--amber)",
  grant: "var(--cyan)",
  mitigate: "var(--green)",
};

/** Map a sampled-packet kind to its attacker source node on the message canvas. */
export const PACKET_SOURCE: Record<string, string> = {
  benign: "CLIENTS",
  ddos: "ATK-DDOS",
  zero_day: "ATK-ZD",
  port_scan: "ATK-DDOS",
  lateral: "ATK-LAT",
};

// --- topology map geometry (segment node centers by active-segment count) ---
export const SLOTS: Record<number, Array<{ x: number; y: number }>> = {
  1: [{ x: 120, y: 140 }],
  2: [
    { x: 120, y: 75 },
    { x: 120, y: 215 },
  ],
  3: [
    { x: 120, y: 70 },
    { x: 64, y: 215 },
    { x: 176, y: 215 },
  ],
  4: [
    { x: 64, y: 75 },
    { x: 176, y: 75 },
    { x: 64, y: 215 },
    { x: 176, y: 215 },
  ],
};

export const SLOT_ORDER = ["server", "internal", "public-facing", "sec-mon"];

export function viewBoxStr(v: ViewBox): string {
  return `${v.x} ${v.y} ${v.w} ${v.h}`;
}

/** A camera box enclosing the given message-graph nodes, padded and floored to a
    minimum size so a single node still reads as a gentle zoom rather than a crop.
    Unknown / empty node sets fall back to the full canvas. */
export function boundingBox(nodeIds: string[], opts?: { pad?: number; min?: number }): ViewBox {
  const pad = opts?.pad ?? 90;
  const min = opts?.min ?? 240;
  const pts = nodeIds.map((id) => NODES[id]).filter(Boolean);
  if (pts.length === 0) return { ...MESSAGE_CANVAS };

  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const p of pts) {
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x);
    maxY = Math.max(maxY, p.y);
  }
  minX -= pad;
  minY -= pad;
  maxX += pad;
  maxY += pad;

  let w = maxX - minX;
  let h = maxY - minY;
  if (w < min) {
    const cx = (minX + maxX) / 2;
    minX = cx - min / 2;
    w = min;
  }
  if (h < min) {
    const cy = (minY + maxY) / 2;
    minY = cy - min / 2;
    h = min;
  }
  return { x: minX, y: minY, w, h };
}
