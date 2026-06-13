/* Packet sprites: turn the sampled packets into dots that stream the network links,
   their position a pure function of the playback clock `t` (so scrubbing and director
   seeks Just Work). No animation library, no per-sprite React state. */
import { NODES, PACKET_SOURCE } from "./graph";
import type { SampledPacket } from "./types";

export const TRAVEL_MS = 900; // time a packet takes to cross from source to network
export const FADE_MS = 220; // lingering fade after arrival
export const MAX_SPRITES = 60; // hard cap on concurrent dots (projector safety)

const KIND_FILL: Record<string, string> = {
  benign: "var(--green)",
  ddos: "var(--red)",
  zero_day: "var(--violet)",
  port_scan: "var(--amber)",
  lateral: "var(--red)",
};

export interface Sprite {
  id: number;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  startMs: number;
  endMs: number;
  kind: string;
  color: string;
}

export interface SpritePos {
  x: number;
  y: number;
  opacity: number;
}

function easeInOut(p: number): number {
  return p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
}

/** Precompute one sprite per packet: a path from its attacker/clients node to the
    network core, arriving at the alert it triggered (or its raw timestamp). */
export function buildSprites(packets: SampledPacket[]): Sprite[] {
  const dst = NODES.NETWORK;
  const sprites: Sprite[] = [];
  packets.forEach((p, i) => {
    const src = NODES[PACKET_SOURCE[p.kind] ?? "CLIENTS"];
    if (!src || !dst) return;
    const arrive = p.alert_ms ?? p.ts_ms;
    const stagger = (i % 6) * 60; // fan out a flow so packets stream, not stack
    sprites.push({
      id: i,
      x1: src.x,
      y1: src.y,
      x2: dst.x,
      y2: dst.y,
      startMs: arrive - TRAVEL_MS - stagger,
      endMs: arrive - stagger,
      kind: p.kind,
      color: KIND_FILL[p.kind] ?? "var(--cyan)",
    });
  });
  return sprites;
}

/** Where a sprite is at time `t`, or null if it isn't in flight. */
export function spriteAt(s: Sprite, t: number): SpritePos | null {
  if (t < s.startMs || t > s.endMs + FADE_MS) return null;
  const dur = Math.max(1, s.endMs - s.startMs);
  const p = Math.min(1, Math.max(0, (t - s.startMs) / dur));
  const e = easeInOut(p);
  return {
    x: s.x1 + (s.x2 - s.x1) * e,
    y: s.y1 + (s.y2 - s.y1) * e,
    opacity: t <= s.endMs ? 1 : Math.max(0, 1 - (t - s.endMs) / FADE_MS),
  };
}

/** All sprites in flight at `t`, capped to the most recent `max`. */
export function activeSprites(
  sprites: Sprite[],
  t: number,
  max = MAX_SPRITES,
): Array<{ s: Sprite; pos: SpritePos }> {
  const out: Array<{ s: Sprite; pos: SpritePos }> = [];
  for (const s of sprites) {
    const pos = spriteAt(s, t);
    if (pos) out.push({ s, pos });
  }
  if (out.length > max) {
    out.sort((a, b) => b.s.startMs - a.s.startMs);
    return out.slice(0, max);
  }
  return out;
}
