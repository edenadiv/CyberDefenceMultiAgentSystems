// @vitest-environment happy-dom
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useLiveConnection } from "./useLiveConnection";

class FakeWS {
  static instances: FakeWS[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  readyState = 0;
  constructor(public url: string) {
    FakeWS.instances.push(this);
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
}

const okFetch = () =>
  vi.fn(
    (_url: string, _init?: RequestInit) =>
      Promise.resolve({ ok: true }) as unknown as Promise<Response>,
  );

beforeEach(() => {
  FakeWS.instances = [];
  vi.stubGlobal("WebSocket", FakeWS as unknown as typeof WebSocket);
  vi.stubGlobal("fetch", okFetch());
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useLiveConnection", () => {
  it("opens no socket when disabled", () => {
    renderHook(() => useLiveConnection(false));
    expect(FakeWS.instances).toHaveLength(0);
  });

  it("connects when enabled and auto-reconnects after a drop", () => {
    const { result } = renderHook(() => useLiveConnection(true));
    expect(FakeWS.instances).toHaveLength(1);

    act(() => FakeWS.instances[0].onopen?.());
    expect(result.current.connected).toBe(true);

    act(() => FakeWS.instances[0].onclose?.());
    expect(result.current.connected).toBe(false);

    act(() => vi.advanceTimersByTime(600)); // backoff (500ms) elapses -> reconnect
    expect(FakeWS.instances.length).toBeGreaterThanOrEqual(2);
  });

  it("posts manual actions to the backend", () => {
    const fetchMock = okFetch();
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useLiveConnection(true));
    result.current.sendDos("public-facing");
    expect(fetchMock).toHaveBeenCalled();
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain("/manual/send-dos");
    expect(opts?.method).toBe("POST");
  });
});
