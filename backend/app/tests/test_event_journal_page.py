from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.database import async_session
from app.core.enums import EventStatus, RunMode, StepStatus
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.external_errors.models import ExternalErrorRecord


async def test_journal_page_finds_oldest_event_in_251(client: AsyncClient):
    base_time = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    async with async_session() as session:
        for i in range(251):
            ev = IntegrationEvent(
                correlation_id=f"corr-{i:04d}",
                source_system="ERP",
                target_system="MES",
                event_type="order.created",
                entity_type="Order",
                entity_id=f"SO-{i:04d}",
                status=EventStatus.FAILED if i == 0 else EventStatus.SUCCESS,
                created_at=base_time + timedelta(seconds=i),
            )
            session.add(ev)
        await session.commit()

    # Legacy endpoint misses the oldest event because of limit 200
    legacy_resp = await client.get("/api/events/journal")
    assert legacy_resp.status_code == 200
    assert len(legacy_resp.json()) == 200
    assert "SO-0000" not in [it["document_number"] for it in legacy_resp.json()]

    # New /page endpoint with q="SO-0000" finds it immediately
    search_resp = await client.get("/api/events/journal/page?q=SO-0000&limit=50")
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["document_number"] == "SO-0000"
    assert data["items"][0]["status"] == "failed"
    assert data["has_more"] is False
    assert data["next_cursor"] is None


async def test_journal_page_101_identical_timestamps_traversal(client: AsyncClient):
    fixed_time = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
    ids_set = set()
    async with async_session() as session:
        for i in range(101):
            ev = IntegrationEvent(
                correlation_id=f"same-time-{i:04d}",
                source_system="ERP",
                target_system="MES",
                event_type="batch.item",
                entity_type="Item",
                entity_id=f"ITEM-{i:04d}",
                status=EventStatus.SUCCESS,
                created_at=fixed_time,
            )
            session.add(ev)
            await session.flush()
            ids_set.add(str(ev.id))
        await session.commit()

    # Page 1: 50 items
    p1 = await client.get("/api/events/journal/page?event_type=batch.item&limit=50")
    assert p1.status_code == 200
    d1 = p1.json()
    assert len(d1["items"]) == 50
    assert d1["has_more"] is True
    assert d1["next_cursor"] is not None

    # Page 2: 50 items
    p2 = await client.get(f"/api/events/journal/page?event_type=batch.item&limit=50&cursor={d1['next_cursor']}")
    assert p2.status_code == 200
    d2 = p2.json()
    assert len(d2["items"]) == 50
    assert d2["has_more"] is True
    assert d2["next_cursor"] is not None

    # Page 3: 1 item
    p3 = await client.get(f"/api/events/journal/page?event_type=batch.item&limit=50&cursor={d2['next_cursor']}")
    assert p3.status_code == 200
    d3 = p3.json()
    assert len(d3["items"]) == 1
    assert d3["has_more"] is False
    assert d3["next_cursor"] is None

    # Verify all 101 unique IDs were retrieved with zero duplicates
    retrieved_ids = [it["id"] for it in d1["items"] + d2["items"] + d3["items"]]
    assert len(retrieved_ids) == 101
    assert len(set(retrieved_ids)) == 101
    assert set(retrieved_ids) == ids_set


async def test_journal_page_new_insertion_does_not_shift_cursor(client: AsyncClient):
    base_time = datetime(2026, 11, 10, 10, 0, 0, tzinfo=timezone.utc)
    async with async_session() as session:
        for i in range(10):
            ev = IntegrationEvent(
                correlation_id=f"shift-test-{i}",
                source_system="SystemA",
                target_system="SystemB",
                event_type="test.shift",
                entity_type="Doc",
                entity_id=f"DOC-{i}",
                status=EventStatus.SUCCESS,
                created_at=base_time + timedelta(seconds=i),
            )
            session.add(ev)
        await session.commit()

    # Get page 1 with limit 5 (items 9, 8, 7, 6, 5)
    r1 = await client.get("/api/events/journal/page?event_type=test.shift&limit=5")
    assert r1.status_code == 200
    d1 = r1.json()
    assert len(d1["items"]) == 5
    page1_docs = [it["document_number"] for it in d1["items"]]
    assert page1_docs == ["DOC-9", "DOC-8", "DOC-7", "DOC-6", "DOC-5"]
    cursor = d1["next_cursor"]

    # Now insert a NEW event into the future (would be at top of chronological list)
    async with async_session() as session:
        new_ev = IntegrationEvent(
            correlation_id="new-future-event",
            source_system="SystemA",
            target_system="SystemB",
            event_type="test.shift",
            entity_type="Doc",
            entity_id="DOC-NEW",
            status=EventStatus.SUCCESS,
            created_at=base_time + timedelta(seconds=100),
        )
        session.add(new_ev)
        await session.commit()

    # Request page 2 with previous cursor
    r2 = await client.get(f"/api/events/journal/page?event_type=test.shift&limit=5&cursor={cursor}")
    assert r2.status_code == 200
    d2 = r2.json()
    assert len(d2["items"]) == 5
    page2_docs = [it["document_number"] for it in d2["items"]]
    assert page2_docs == ["DOC-4", "DOC-3", "DOC-2", "DOC-1", "DOC-0"]
    # No items from page 1 duplicated, no items lost!


async def test_journal_page_with_external_error(client: AsyncClient):
    event_time = datetime(2026, 11, 15, 14, 0, 0, tzinfo=timezone.utc)
    async with async_session() as session:
        ev = IntegrationEvent(
            correlation_id="err-corr-1",
            source_system="1C",
            target_system="Ozon",
            event_type="StockUpdate",
            entity_type="Stock",
            entity_id="SKU-999",
            status=EventStatus.FAILED,
            created_at=event_time,
        )
        session.add(ev)
        await session.flush()

        err = ExternalErrorRecord(
            event_id=ev.id,
            source_system="1C",
            target_system="Ozon",
            operation="UpdateStocks",
            normalized_code="OZON_TIMEOUT",
            normalized_message="Connection timed out",
            human_title="Таймаут шлюза Ozon",
            human_summary="Сервер Ozon не ответил вовремя",
            hint="Попробуйте повторить операцию через 5 минут",
            created_at=event_time + timedelta(seconds=1),
        )
        session.add(err)
        await session.commit()

    resp = await client.get("/api/events/journal/page?q=SKU-999")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["human_title"] == "Таймаут шлюза Ozon"
    assert item["human_summary"] == "Сервер Ozon не ответил вовремя"
    assert item["last_error_code"] == "OZON_TIMEOUT"
    assert item["hint"] == "Попробуйте повторить операцию через 5 минут"
    assert item["requires_attention"] is True


async def test_journal_page_validations(client: AsyncClient):
    # Invalid limit < 1
    r_bad_limit = await client.get("/api/events/journal/page?limit=0")
    assert r_bad_limit.status_code == 422

    # Invalid limit > 100
    r_bad_limit_high = await client.get("/api/events/journal/page?limit=101")
    assert r_bad_limit_high.status_code == 422

    # Invalid date range (from > to)
    r_bad_dates = await client.get("/api/events/journal/page?date_from=2026-11-20T10:00:00Z&date_to=2026-11-10T10:00:00Z")
    assert r_bad_dates.status_code == 422

    # Malformed cursor
    r_bad_cursor = await client.get("/api/events/journal/page?cursor=not-a-valid-cursor")
    assert r_bad_cursor.status_code == 422
