/* React lifecycle around the live WebSocket: connects when enabled, folds frames into a
   LiveState via the pure reducer, and exposes the manual/control actions as REST posts. */
import { useEffect, useState } from "react";

import { type LiveState, initialLiveState, liveReduce } from "./liveStore";

const meta = import.meta as unknown as { env?: Record<string, string | undefined> };
const env = meta.env ?? {};
const HTTP = env.VITE_LIVE_HTTP ?? "http://localhost:8000";
const TOKEN = env.VITE_LIVE_TOKEN ?? "changeme";
const WS = HTTP.replace(/^http/, "ws") + "/ws/events";

export interface LiveConnection {
  state: LiveState;
  connected: boolean;
  sendDos: (segment: string) => void;
  sendLegal: (segment: string) => void;
  setRunMode: (m: "auto" | "step") => void;
  next: () => void;
}

export function useLiveConnection(enabled: boolean): LiveConnection {
  const [state, setState] = useState<LiveState>(initialLiveState);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setState(initialLiveState);
      setConnected(false);
      return;
    }
    let closed = false;
    let ws: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;

    // Exponential backoff so a server restart or network blip reconnects on its own.
    function schedule(): void {
      if (closed || retry) return;
      const delay = Math.min(5000, 500 * 2 ** attempt);
      attempt += 1;
      retry = setTimeout(() => {
        retry = null;
        connect();
      }, delay);
    }

    function connect(): void {
      if (closed) return;
      try {
        ws = new WebSocket(`${WS}?token=${encodeURIComponent(TOKEN)}`);
      } catch {
        schedule();
        return;
      }
      ws.onopen = () => {
        if (closed) return;
        attempt = 0;
        setConnected(true);
      };
      ws.onmessage = (e) => {
        try {
          setState((s) => liveReduce(s, JSON.parse(e.data)));
        } catch {
          /* ignore malformed frame */
        }
      };
      ws.onclose = () => {
        if (closed) return;
        setConnected(false);
        schedule();
      };
      ws.onerror = () => ws?.close(); // -> onclose -> reconnect
    }

    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      ws?.close();
      setConnected(false);
    };
  }, [enabled]);

  const post = (path: string, body: Record<string, unknown>): void => {
    void fetch(`${HTTP}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${TOKEN}` },
      body: JSON.stringify(body),
    }).catch(() => {});
  };

  return {
    state,
    connected,
    sendDos: (segment) => post("/manual/send-dos", { segment }),
    sendLegal: (segment) => post("/manual/send-legal", { segment }),
    setRunMode: (mode) => post("/control/mode", { mode }),
    next: () => post("/control/next", {}),
  };
}
