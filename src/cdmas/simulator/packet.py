"""Packet model — the unit of the synthetic traffic stream (SDD §6.1.2)."""

from pydantic import BaseModel


class Packet(BaseModel):
    src_ip: str
    dst_ip: str
    port: int
    protocol: str = "TCP"
    pkt_size: int = 512
    freq: float = 1.0  # packets/sec this flow represents
    ts_ms: float = 0.0
