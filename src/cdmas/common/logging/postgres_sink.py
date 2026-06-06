"""PostgreSQL event sink (SDD §7.1) — async writes via SQLAlchemy + asyncpg."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Float, Integer, String
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from cdmas.common.logging.event_log import EventLog, EventSink


class Base(DeclarativeBase):
    pass


class EventRow(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    lamport_ts: Mapped[int] = mapped_column(Integer)
    wall_ms: Mapped[float] = mapped_column(Float)
    event_type: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[str] = mapped_column(String)
    agent_id: Mapped[str] = mapped_column(String, index=True)
    agent_type: Mapped[str] = mapped_column(String, index=True)
    segment: Mapped[str | None] = mapped_column(String, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision_trace: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class PostgresSink(EventSink):
    def __init__(self, db_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(db_url, future=True)
        self._session = async_sessionmaker(self._engine, expire_on_commit=False)

    async def create_schema(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def write(self, event: EventLog) -> None:
        data = event.model_dump(mode="json")
        row = EventRow(
            event_id=data["event_id"],
            lamport_ts=data["lamport_ts"],
            wall_ms=data["wall_ms"],
            event_type=data["event_type"],
            timestamp=data["timestamp"],
            agent_id=data["agent_id"],
            agent_type=data["agent_type"],
            segment=data["segment"],
            payload=data["payload"],
            latency_ms=data["latency_ms"],
            decision_trace=data["decision_trace"],
        )
        async with self._session() as session:
            session.add(row)
            await session.commit()

    async def close(self) -> None:
        await self._engine.dispose()
