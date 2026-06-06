# Phase 2: Simulator Implementation Plan

> Detailed plan for the FastAPI network simulation engine. Builds on Phase 1
> (`cdmas.common.*`). Execution order: 2A (deterministic engine core) → 2B (state/
> resources/engine) → 2C (REST/WS/auth/client). The in-process engine (2A/2B) is the
> priority: it unblocks the Phase 3 vertical slice and the Phase 8 harness without HTTP.

**Goal:** A standalone simulator modeling the 4-segment network — synthetic traffic,
attack injection, deterministic clock, segment state, resource accounting — exposed both
in-process (for agents/tests) and over a FastAPI REST + WebSocket API.

**Architecture:** Pure-Python deterministic core (no I/O) wrapped by a thin FastAPI layer.
Determinism via injected `Clock` + seeded numpy RNG. Agents and the validator harness talk
to the core through a `SimClientProtocol`; in tests they use the in-process implementation,
in production the httpx-backed `SimClient` hitting the REST API.

## Data contracts (pinned — Phases 3 & 8 depend on these)

```python
# common/timing/clock.py
class Clock(Protocol):
    def now_ms(self) -> float: ...
    async def sleep(self, ms: float) -> None: ...
class WallClock(Clock): ...        # time.monotonic()*1000 ; asyncio.sleep
class ManualClock(Clock):          # deterministic; advance(ms) wakes sleepers
    def advance(self, ms: float) -> None: ...

# simulator/packet.py
class Packet(BaseModel):
    src_ip: str; dst_ip: str; port: int; protocol: str
    pkt_size: int; freq: float; ts_ms: float

# simulator/attacks.py
class AttackSpec(BaseModel):
    type: AttackType; segment: Segment; intensity: float = 1.0
    duration_ms: int = 0; start_ms: float = 0.0; mode: str = "independent"  # | "coordinated"
class GroundTruth(BaseModel):      # what was actually injected (for DR/FPR)
    attacks: list[AttackSpec]
    def is_attack(self, segment: Segment, ts_ms: float) -> bool: ...

# simulator/models.py
class ActionRequest(BaseModel): type: ResponseType; segment: Segment; params: dict[str, Any] = {}
class ActionResult(BaseModel): accepted: bool; effectiveness: float; detail: str = ""
class InjectAttackRequest(BaseModel): spec: AttackSpec
class SegmentState(BaseModel): segment: Segment; health: str; flows_per_s: float; active_defenses: list[str]
class StateSnapshot(BaseModel): sim_ms: float; segments: list[SegmentState]; resource_overhead: float; auctions: list[dict]
class MetricsSnapshot(BaseModel):  # placeholder values until Phase 6 analytics fills them
    dr: float; fpr: float; mttr_alert_ms: float; mttr_response_ms: float
    availability: float; resource_overhead: float; social_welfare: float; attacker_utility: float
class TopologyView(BaseModel): segments: list[Segment]; adjacency: dict[str, list[str]]

# simulator/client.py — the interface agents depend on (Phase 3)
class SimClientProtocol(Protocol):
    async def packets(self, segment: Segment, n: int) -> list[Packet]: ...
    async def apply_action(self, req: ActionRequest) -> ActionResult: ...
    def topology(self) -> TopologyView: ...
    def state(self) -> StateSnapshot: ...

# simulator/engine.py — in-process composition (Phase 8 harness binds to this)
class InProcessSimulator(SimClientProtocol):
    def __init__(self, *, clock: Clock, segments: list[Segment], seed: int = 0): ...
    def tick(self) -> None: ...                 # advance one sim step, regenerate traffic
    def inject(self, spec: AttackSpec) -> None: ...
    def ground_truth(self) -> GroundTruth: ...
```

**Adjacency (fixed default):** `internal↔server`, `server↔public-facing`,
`sec-mon↔{internal,server,public-facing}` (monitoring sees all). Lateral movement only
along edges.

## Task checklist (TDD — full detail in the end-to-end plan's Phase 2 table)

- [ ] 2.0 `Clock`/`WallClock`/`ManualClock` — `sleep` resolves only after `advance`.
- [ ] 2.1 `SimClock` speed scaling — 10× ⇒ 10ms wall = 100ms sim (under ManualClock).
- [ ] 2.2 `NetworkTopology` — 4 segments, symmetric adjacency, lateral only along edges.
- [ ] 2.3 `Packet` + `TrafficGenerator` — seeded numpy Gaussian; same seed ⇒ identical stream.
- [ ] 2.4 `AttackInjector` DDoS/scan — DDoS raises PPS + randomized src IPs; scan distinct ports.
- [ ] 2.5 `AttackInjector` lateral/zero-day — lateral on adjacency; zero-day = OOD vector.
- [ ] 2.6 `StateManager` + `apply_action` — THROTTLE cuts DDoS; QUARANTINE isolates; health transitions.
- [ ] 2.7 `ResourcePool` + 40% cap — over-cap grants rejected; warn 35 / crit 40.
- [ ] 2.8 `auth` token + per-agent rate limit — bad token→401; burst→429.
- [ ] 2.9 REST endpoints — `/packets/{segment} /action /topology /state /metrics /inject-attack`.
- [ ] 2.10 WebSocket `/ws/state` — ordered snapshots on each tick.
- [ ] 2.11 `SimClient` (httpx) + `InProcessSimulator` both satisfy `SimClientProtocol`.
- [ ] 2.12 `__main__` uvicorn entrypoint + container smoke.

**DoD:** `pytest tests/simulator` green (ManualClock); FastAPI TestClient integration test
(inject→packets→action→metrics); `docker compose up simulator` serves `/topology`.
Covers SRS §5.1, FR-23 hook.
