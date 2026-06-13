import pytest

from cdmas.validator.export import build_export
from cdmas.validator.scenarios import SCENARIOS


@pytest.mark.slow
async def test_build_export_structure():
    data = await build_export()

    assert [r["scenario"] for r in data["replays"]] == [name for name, _, _ in SCENARIOS]
    for replay in data["replays"]:
        assert replay["events"]
        assert "metrics" in replay
        assert replay["duration_ms"] > 0
        assert set(replay["topology"]["adjacency"]) == set(replay["topology"]["segments"])

    assert data["replays"][0]["topology"]["segments"] == ["public-facing"]
    contention = next(r for r in data["replays"] if "Contention" in r["scenario"])
    assert set(contention["topology"]["segments"]) == {
        "internal",
        "server",
        "public-facing",
        "sec-mon",
    }

    assert len(data["validation"]) == 6
    assert all("constraints" in v for v in data["validation"])


@pytest.mark.slow
async def test_export_includes_representative_packet_samples():
    from cdmas.simulator.sampling import MAX_TOTAL

    data = await build_export()

    for replay in data["replays"]:
        assert "packets" in replay and isinstance(replay["packets"], list)
        assert "messages" in replay
        assert len(replay["packets"]) <= MAX_TOTAL  # budget respected per scenario
        for p in replay["packets"]:
            assert {
                "src_ip",
                "dst_ip",
                "port",
                "kind",
                "segment",
                "ts_ms",
                "alert_ms",
            } <= set(p)

    all_pkts = [p for r in data["replays"] for p in r["packets"]]
    assert all_pkts, "expected sampled packets in the export"
    # The real attacker signatures survive into the replay.
    assert any(p["src_ip"].startswith("203.0.") for p in all_pkts)  # DDoS bots
    kinds = {p["kind"] for p in all_pkts}
    assert "ddos" in kinds and "benign" in kinds
    # At least one packet is correlated to the alert it triggered.
    assert any(p["alert_ms"] is not None for p in all_pkts)


@pytest.mark.slow
async def test_export_stays_within_size_budget():
    # The dashboard loads this bundle verbatim; the packet/decision enrichment must not
    # bloat the offline file. Current size ~580 KB; fail loudly before it runs away.
    import json

    data = await build_export()
    size = len(json.dumps(data, indent=2).encode("utf-8"))
    assert size < 700_000, f"replay bundle too large: {size} bytes"
