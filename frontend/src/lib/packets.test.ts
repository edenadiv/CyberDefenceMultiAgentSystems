import { describe, expect, it } from "vitest";

import { NODES } from "./graph";
import { FADE_MS, activeSprites, buildSprites, spriteAt } from "./packets";
import type { SampledPacket } from "./types";

const pkt = (over: Partial<SampledPacket> = {}): SampledPacket => ({
  src_ip: "203.0.1.1",
  dst_ip: "10.2.0.1",
  port: 443,
  protocol: "TCP",
  pkt_size: 512,
  freq: 5000,
  ts_ms: 1000,
  kind: "ddos",
  segment: "public-facing",
  alert_ms: 1200,
  ...over,
});

describe("buildSprites", () => {
  it("routes a ddos packet from the DDoS attacker node to NETWORK, arriving at the alert", () => {
    const [s] = buildSprites([pkt()]);
    expect(s.x1).toBe(NODES["ATK-DDOS"].x);
    expect(s.y1).toBe(NODES["ATK-DDOS"].y);
    expect(s.x2).toBe(NODES.NETWORK.x);
    expect(s.y2).toBe(NODES.NETWORK.y);
    expect(s.endMs).toBe(1200); // alert_ms, first-in-flow has no stagger
    expect(s.startMs).toBeLessThan(s.endMs); // travels in
  });

  it("falls back to ts_ms when a packet has no correlated alert", () => {
    const [s] = buildSprites([pkt({ alert_ms: null, ts_ms: 800 })]);
    expect(s.endMs).toBe(800);
  });

  it("routes benign traffic from the clients node", () => {
    const [s] = buildSprites([pkt({ kind: "benign", src_ip: "10.2.0.7" })]);
    expect(s.x1).toBe(NODES.CLIENTS.x);
  });
});

describe("spriteAt", () => {
  const [s] = buildSprites([pkt()]);

  it("is hidden before departure and after arrival+fade", () => {
    expect(spriteAt(s, s.startMs - 1)).toBeNull();
    expect(spriteAt(s, s.endMs + FADE_MS + 1)).toBeNull();
  });

  it("sits at the source at departure and the destination at arrival", () => {
    const start = spriteAt(s, s.startMs)!;
    expect(start.x).toBeCloseTo(s.x1, 5);
    expect(start.y).toBeCloseTo(s.y1, 5);
    const end = spriteAt(s, s.endMs)!;
    expect(end.x).toBeCloseTo(s.x2, 5);
    expect(end.y).toBeCloseTo(s.y2, 5);
  });

  it("fades out after arrival", () => {
    const arrived = spriteAt(s, s.endMs)!;
    const fading = spriteAt(s, s.endMs + FADE_MS / 2)!;
    expect(arrived.opacity).toBeGreaterThan(fading.opacity);
  });
});

describe("activeSprites", () => {
  it("caps the number of concurrent sprites", () => {
    // 50 packets all in flight at the same moment.
    const many = Array.from({ length: 50 }, (_, i) => pkt({ ts_ms: 1000, alert_ms: 1000, src_ip: `203.0.0.${i}` }));
    const sprites = buildSprites(many);
    const active = activeSprites(sprites, 600, 10);
    expect(active.length).toBeLessThanOrEqual(10);
  });
});
