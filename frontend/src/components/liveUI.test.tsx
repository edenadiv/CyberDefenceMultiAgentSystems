// @vitest-environment happy-dom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(cleanup);

import { ReplayContext, type ReplayCtx } from "../lib/replayContext";
import type { Metrics } from "../lib/types";
import { Header } from "./Header";
import { ReplayControls } from "./ReplayControls";

const METRICS: Metrics = {
  dr: 0,
  fpr: 0,
  mttr_alert_ms: 0,
  mttr_response_ms: 0,
  availability: 1,
  resource_overhead: 0,
  social_welfare: 0,
  attacker_utility: 0,
  coalition_ms: null,
  evasion_rate: null,
  concurrent_incidents: 0,
};

function ctx(overrides: Partial<ReplayCtx> = {}): ReplayCtx {
  const topology = { segments: [], adjacency: {} };
  return {
    data: {
      topology,
      replay: { scenario: "", duration_ms: 1, topology, events: [], metrics: METRICS },
      validation: [],
    },
    scenarios: ["A"],
    scenario: 0,
    selectScenario: vi.fn(),
    duration: 1,
    t: 0,
    setT: vi.fn(),
    playing: false,
    setPlaying: vi.fn(),
    speed: 1,
    setSpeed: vi.fn(),
    derived: {
      segments: {},
      alerts: [],
      flows: [],
      coalitions: [],
      overhead: 0,
      counts: { alerts: 0, classified: 0, responses: 0, votes: 0 },
    },
    director: {
      active: false,
      beats: [],
      index: 0,
      mode: "manual",
      start: vi.fn(),
      stop: vi.fn(),
      next: vi.fn(),
      prev: vi.fn(),
      goto: vi.fn(),
      setMode: vi.fn(),
    },
    viewMode: "live",
    setViewMode: vi.fn(),
    live: {
      connected: true,
      conn: { agents_connected: 5, agents_total: 5, bus_connected: true, stream_connected: true },
      sim: { mode: "auto", paused: false, awaiting_next: false, round: 7 },
      segments: ["public-facing", "internal"],
      sendDos: vi.fn(),
      sendLegal: vi.fn(),
      setRunMode: vi.fn(),
      next: vi.fn(),
    },
    ...overrides,
  };
}

const provide = (c: ReplayCtx, node: ReactNode) =>
  render(<ReplayContext.Provider value={c}>{node}</ReplayContext.Provider>);

const btn = (name: RegExp) => screen.getByRole("button", { name }) as HTMLButtonElement;

describe("LiveControls", () => {
  it("Send DoS calls the action with the selected segment", () => {
    const c = ctx();
    provide(c, <ReplayControls />);
    fireEvent.click(btn(/Send DoS/));
    expect(c.live.sendDos).toHaveBeenCalledWith("public-facing");
  });

  it("Next is disabled when the sim is not awaiting it", () => {
    provide(ctx(), <ReplayControls />);
    expect(btn(/Next/).disabled).toBe(true);
  });

  it("Next is enabled when the sim is awaiting it", () => {
    const base = ctx();
    provide(
      ctx({ live: { ...base.live, sim: { ...base.live.sim, awaiting_next: true } } }),
      <ReplayControls />,
    );
    expect(btn(/Next/).disabled).toBe(false);
  });

  it("disables actions while disconnected", () => {
    provide(ctx({ live: { ...ctx().live, connected: false } }), <ReplayControls />);
    expect(btn(/Send DoS/).disabled).toBe(true);
  });
});

describe("Header", () => {
  const withRouter = (c: ReplayCtx) =>
    render(
      <MemoryRouter>
        <ReplayContext.Provider value={c}>
          <Header onStepThrough={vi.fn()} />
        </ReplayContext.Provider>
      </MemoryRouter>,
    );

  it("shows connection badges in live mode", () => {
    withRouter(ctx());
    expect(screen.getByText(/Agents 5\/5/)).toBeTruthy();
  });

  it("shows the Step-by-Step button in replay mode", () => {
    withRouter(ctx({ viewMode: "replay" }));
    expect(screen.getByRole("button", { name: /Step by Step/ })).toBeTruthy();
  });
});
