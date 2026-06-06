# Collaborative Cyber-Defense Multi-Agent System (CDMAS)

A decentralized **Multi-Agent System (MAS)** for automated cyber-defense and incident
response, validated inside a simulated four-segment corporate network. Autonomous
**BDI (Belief–Desire–Intention)** agents collaboratively monitor, detect, classify, and
respond to attacks with a target **Mean Time to Respond (MTTR) < 1 second**.

> ⚠️ **This is a simulation and validation platform, not a live network appliance.**
> Every "attacker" is a simulated agent. The system proves, via an automated constraint
> checker, that it meets the quantitative targets defined in the SRS.

**Status: complete.** All six SRS validation scenarios pass (Social Welfare 0.92–1.00),
the FR constraint checker reports 32 functional requirements passing / 0 failing, and the
React command-center dashboard renders a recorded incident with a guided tutorial.

Source specifications: [`docs/`](docs/) (SRS + SDD). Implementation plans:
[`docs/superpowers/plans/`](docs/superpowers/plans/).

---

## The agents

**5 defense agent types**, each a BDI agent running a `perceive → reason → act` loop:

| Agent | Role | Headline responsibility |
|-------|------|-------------------------|
| **TMA** – Traffic Monitor      | The eyes          | Sample traffic, rolling baseline, flag >2σ anomalies, alert < 100 ms |
| **ACA** – Anomaly Classifier   | The analyst       | Hybrid ML classify < 200 ms (RandomForest + nearest-neighbour novelty), online learning |
| **RCA** – Response Coordinator | Incident commander| Attack-type-aware proportional response < 500 ms; quarantine via majority vote |
| **TIA** – Threat Intelligence  | Memory / broker   | Global threat map, cross-segment correlation, coalition formation |
| **RAA** – Resource Allocator   | Logistics         | Sealed-bid auction, 40% host-overhead cap |

**4 attacker agent types:** DDoS, Port Scanner, Lateral Movement, Zero-Day Emulator.

## Coordination mechanisms (SDD §4)

Publish-Subscribe bus (FIPA-ACL, Lamport clocks, idempotent dedup) · sealed-bid
first-price auction · TIA-triggered coalition formation · majority-vote quarantine
escalation (BLOCK fallback) · heartbeat-based failover (coverage reassigned < 2 s).

## Validated targets

| Metric | Target | Result (representative) |
|--------|--------|--------------------------|
| Detection Rate | > 90% | ✅ |
| False Positive Rate | < 10% | ✅ |
| MTTR (response) | < 1000 ms | ✅ |
| System Availability | > 99% | ✅ |
| Resource Overhead | < 40% | ✅ |
| Social Welfare | ≥ 0.80 | ✅ 0.92–1.00 |

Run the gate yourself: `make validate` (prints the six-scenario report) or
`make acceptance` (pytest).

---

## Tech stack

Python 3.11 + asyncio · Apache Kafka (`aiokafka`) · scikit-learn + numpy · FastAPI +
Uvicorn + WebSocket · React + D3.js + Recharts (Vite) · structlog → PostgreSQL ·
Docker Compose. Tests: pytest (128) + vitest (4). Lint: ruff. Types: mypy --strict.

## Repository layout

```
src/cdmas/
├── common/        # BDI core, FIPA-ACL messaging + bus (in-memory + Kafka), models, logging, timing
├── simulator/     # FastAPI network sim: topology, traffic, attack injector, clock, state, REST+WS
├── agents/        # TMA, ACA, RCA, TIA, RAA + attackers + factory + runner/entrypoints
├── coordination/  # auction, voting, coalition, failover protocols
├── analytics/     # metrics, per-agent utilities, Social Welfare, reports
└── validator/     # FR-01..34 constraint checkers, scenario harness, 6 scenarios, runner, export
frontend/          # React command-center dashboard (Dashboard / Inspector / Validator) + tutorial
deploy/dockerfiles/  docker-compose.yml  .github/workflows/ci.yml
```

---

## Quick start

```bash
# Backend (Python)
make install        # venv + package with dev extras
make test           # unit suite (128 tests)
make validate       # run the six SRS scenarios and print the report
make lint typecheck # ruff + mypy --strict

# Dashboard (beautiful UI + guided tutorial)
cd frontend && npm install && npm run dev   # http://localhost:5173
#   then click "▶ Guided Tour" for the dynamic walkthrough

# Full containerized system
docker compose up                       # infra (Kafka + PostgreSQL)
docker compose --profile app up --build # + simulator, 4 agent trios, TIA/RAA, dashboard
```

The dashboard ships with a recorded multi-segment incident
(`frontend/src/data/replay.json`, regenerate with `python -m cdmas.validator.export`),
so it runs standalone; it can also stream from a live simulator's WebSocket.

## Dashboard

Three pages (SDD §6.2), over a deterministic **replay engine** that plays the recorded
scenario on a scrubbable timeline:

- **Dashboard** — network topology with live health, animated agent message-flow +
  coalition overlay, chronological alert feed, live metrics vs SRS targets, RAA resource panel.
- **Agent Inspector** — any agent's live BDI state: current intention, ranked desires,
  and a streaming strategy trace.
- **Validator** — all six scenarios with PASS/FAIL, Social Welfare, and the per-FR
  constraint matrix.
- **Guided Tour** — a 6-step dynamic tutorial that drives the replay through the full
  detect → classify → respond → coordinate lifecycle.

## Development

Built test-first across 8 phases (Foundations → Simulator → Defense Agents →
Coordination → Attackers → Observability → Dashboard → Validation). Plans in
`docs/superpowers/plans/`.
