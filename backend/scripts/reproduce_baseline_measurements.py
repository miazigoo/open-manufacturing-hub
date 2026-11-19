import asyncio
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ["OMH_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from datetime import datetime, timedelta, timezone
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.artifacts.service import create_artifact
from app.core.database import Base, async_session, engine
from app.core.enums import ArtifactType, EventStatus, RunMode, StepStatus
from app.enterprise_runtime.models import EnterpriseQueueStatus, IntegrationQueueMessage
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.main import app


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_1_events_journal():
    print("\n--- Check 1: 251 Events in Journal ---")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    base_time = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    async with async_session() as session:
        for i in range(251):
            ev = IntegrationEvent(
                correlation_id=f"corr-{i:04d}",
                source_system="ERP",
                target_system="MES",
                event_type="order.created",
                entity_type="Order",
                entity_id=f"ORD-{i:04d}",
                status=EventStatus.SUCCESS,
                created_at=base_time + timedelta(seconds=i),
            )
            session.add(ev)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/events/journal")
        content_bytes = len(resp.content)
        items = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Items returned: {len(items)} (expected 200 out of 251)")
        print(f"Response size: {content_bytes} bytes (approx 136,210 bytes)")
        
        # Check if the oldest event ORD-0000 is present
        entity_ids = [it.get("document_number") or it.get("entity_id") for it in items]
        has_oldest = "ORD-0000" in entity_ids
        print(f"Contains oldest event (ORD-0000): {has_oldest} (expected False because of 200 limit)")


async def check_2_queue_monitor():
    print("\n--- Check 2: 1,000 Queue Records ---")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    payload_str = "x" * 4096
    payload_obj = {"data": payload_str}
    base_time = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)

    async with async_session() as session:
        for i in range(1000):
            msg = IntegrationQueueMessage(
                business_object="Order",
                operation="sync",
                status=EnterpriseQueueStatus.WAITING,
                attempts=0,
                max_attempts=3,
                payload_json=payload_obj,
                original_payload_json=payload_obj,
                created_at=base_time + timedelta(seconds=i),
            )
            session.add(msg)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/queue")
        content_bytes = len(resp.content)
        items = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Items returned: {len(items)} (expected 1,000)")
        print(f"Response size: {content_bytes} bytes (approx 9,010,001 bytes)")


async def check_3_event_timeline():
    print("\n--- Check 3: Event with 1MB Artifact Timeline ---")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    large_str = "a" * 1048576
    large_json = {"big_payload": large_str}

    async with async_session() as session:
        ev = IntegrationEvent(
            correlation_id="corr-large",
            source_system="ERP",
            target_system="WMS",
            event_type="shipment.created",
            entity_type="Shipment",
            entity_id="SHP-001",
            status=EventStatus.SUCCESS,
        )
        session.add(ev)
        await session.flush()

        run = EventRun(
            event_id=ev.id,
            run_number=1,
            mode=RunMode.NORMAL,
            status=EventStatus.SUCCESS,
        )
        session.add(run)
        await session.flush()

        step = EventStep(
            run_id=run.id,
            step_order=1,
            step_name="step_transform",
            status=StepStatus.SUCCESS,
        )
        session.add(step)
        await session.flush()

        await create_artifact(
            session,
            event_id=ev.id,
            run_id=run.id,
            step_id=step.id,
            artifact_type=ArtifactType.RAW_PAYLOAD,
            name="transformed_payload.json",
            content=large_json,
        )
        await session.commit()
        event_id = ev.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/events/{event_id}/timeline")
        content_bytes = len(resp.content)
        print(f"Status: {resp.status_code}")
        print(f"Response size: {content_bytes} bytes (approx 2,098,907 bytes)")
        data = resp.json()
        # Verify artifact is present in both run.artifacts and step.artifacts
        runs = data.get("runs", [])
        if runs:
            run_artifacts = runs[0].get("artifacts", [])
            step_artifacts = runs[0].get("steps", [])[0].get("artifacts", [])
            print(f"Artifact in run.artifacts: {len(run_artifacts)}, in step.artifacts: {len(step_artifacts)}")


async def main():
    await check_1_events_journal()
    await check_2_queue_monitor()
    await check_3_event_timeline()


if __name__ == "__main__":
    asyncio.run(main())
