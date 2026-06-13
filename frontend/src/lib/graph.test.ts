import { describe, expect, it } from "vitest";

import { MESSAGE_CANVAS, NODES, boundingBox } from "./graph";

describe("boundingBox", () => {
  it("falls back to the full canvas when no nodes match", () => {
    expect(boundingBox([])).toEqual(MESSAGE_CANVAS);
    expect(boundingBox(["does-not-exist"])).toEqual(MESSAGE_CANVAS);
  });

  it("encloses every requested node", () => {
    const ids = ["TMA", "ACA", "RCA"];
    const b = boundingBox(ids);
    for (const id of ids) {
      const n = NODES[id];
      expect(n.x).toBeGreaterThanOrEqual(b.x);
      expect(n.x).toBeLessThanOrEqual(b.x + b.w);
      expect(n.y).toBeGreaterThanOrEqual(b.y);
      expect(n.y).toBeLessThanOrEqual(b.y + b.h);
    }
  });

  it("zooms in: a single-node box is smaller than the full canvas", () => {
    const b = boundingBox(["ACA"]);
    expect(b.w).toBeLessThan(MESSAGE_CANVAS.w);
    expect(b.h).toBeLessThan(MESSAGE_CANVAS.h);
    // ...but not degenerate — the minimum keeps it readable.
    expect(b.w).toBeGreaterThanOrEqual(240);
    expect(b.h).toBeGreaterThanOrEqual(240);
  });
});
