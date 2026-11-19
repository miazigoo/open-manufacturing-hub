from __future__ import annotations

import io
import csv
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, select

from app.audit.models import AuditEvent
from app.core.database import get_session
from app.core.enums import IntegrationMessageDirection, IntegrationMessageStatus, IntegrationPackageStatus
from app.data_inbox.models import InboxRecord, InboxTemplate
from app.main import app
from app.marking_code_pools.models import MarkingCodePoolExport
from app.onec_workbench.models import IntegrationMessage
from app.packages.models import InstalledPackage
from app.polling.models import PollingJob, PollingJobRun, PollingJobStatus
from app.printing.models import PrintJob, PrintJobLine, PrintJobStatus, PrintLineStatus, PrintPrinter
from app.printing.service import _recalculate_job
from app.production.models import BackupRecord, BackupStatus, BackupType


async def ensure_package(session, package_id: str, name: str):
    res = await session.execute(select(InstalledPackage).where(InstalledPackage.package_id == package_id))
    pkg = res.scalar_one_or_none()
    if not pkg:
        pkg = InstalledPackage(
            package_id=package_id,
            name=name,
            version="0.1.0",
            status=IntegrationPackageStatus.ENABLED,
            enabled=True,
            manifest_json={},
        )
        session.add(pkg)
    else:
        pkg.enabled = True
        pkg.status = IntegrationPackageStatus.ENABLED
    await session.commit()


@pytest.mark.asyncio
async def test_audit_list_summary_and_details(session):
    event = AuditEvent(
        action="test.action",
        category="test",
        summary="Test audit event",
        actor_username="admin",
        before_json={"sensitive_key": "old_secret_value"},
        after_json={"sensitive_key": "new_secret_value"},
        details_json={"full_context": "lots of details"},
    )
    session.add(event)
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        try:
            # List endpoint
            resp = await client.get("/api/audit")
            assert resp.status_code == 200
            data = resp.json()
            assert "items" in data
            assert len(data["items"]) >= 1
            item = next(i for i in data["items"] if i["id"] == str(event.id))
            assert item["action"] == "test.action"
            # Crucial check: heavy payloads MUST NOT be in the summary
            assert "before_json" not in item
            assert "after_json" not in item
            assert "details_json" not in item

            # Detail endpoint loads full JSON
            detail_resp = await client.get(f"/api/audit/{event.id}")
            assert detail_resp.status_code == 200
            detail = detail_resp.json()
            assert detail["before_json"] == {"sensitive_key": "old_secret_value"}
            assert detail["after_json"] == {"sensitive_key": "new_secret_value"}
        finally:
            app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_inbox_template_lazy_loading(session):
    tmpl = InboxTemplate(
        slug=f"tmpl_{uuid4().hex[:8]}",
        name="Template with many records",
        schema_json={},
    )
    session.add(tmpl)
    await session.flush()

    for i in range(100):
        rec = InboxRecord(
            template_id=tmpl.id,
            status="received",
            payload_json={"row": i, "data": "x" * 100},
        )
        session.add(rec)
    await session.commit()

    from sqlalchemy.orm import class_mapper
    mapper = class_mapper(InboxTemplate)
    assert mapper.relationships["records"].lazy == "noload"


@pytest.mark.asyncio
async def test_inbox_records_csv_streaming(session):
    tmpl = InboxTemplate(
        slug=f"tmpl_{uuid4().hex[:8]}",
        name="CSV stream template",
        schema_json={},
    )
    session.add(tmpl)
    await session.flush()

    for i in range(20):
        rec = InboxRecord(
            template_id=tmpl.id,
            status="received",
            payload_json={"name": f"Товар, №{i}", "count": i * 10},
        )
        session.add(rec)
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = await client.get(f"/api/inbox-records/export.csv?template_id={tmpl.id}")
            assert resp.status_code == 200
            assert "text/csv" in resp.headers.get("content-type", "")
            
            csv_text = resp.text
            reader = csv.reader(io.StringIO(csv_text))
            rows = list(reader)
            assert len(rows) == 21
            assert rows[0][0] == "id"
            assert "status" in rows[0]
        finally:
            app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_marking_code_pools_overview(session):
    await ensure_package(session, "omh-package-onec", "1C Package")

    for i in range(5):
        exp = MarkingCodePoolExport(
            source_system="1C_ERP",
            order_number=f"ORD-{i}",
            file_name=f"export_{i}.csv",
            file_path=f"/tmp/export_{i}.csv",
            total_codes=1000,
            content_sha256="dummy_sha256",
            status="error" if i % 2 == 1 else "success",
            error_message="Device timeout" if i % 2 == 1 else None,
            metadata_json={"order": i},
        )
        session.add(exp)
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = await client.get("/api/marking-code-pools/overview")
            assert resp.status_code == 200
            data = resp.json()
            assert "settings" in data
            assert data["total_exports"] >= 5
            assert len(data["recent_errors"]) <= 3
            assert data["latest_export"]["order_number"] == "ORD-4"
        finally:
            app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_onec_workbench_list_messages_defers_payload(session):
    await ensure_package(session, "omh-package-onec", "1C Package")

    msg = IntegrationMessage(
        direction=IntegrationMessageDirection.INBOUND,
        source_system="1C_ERP",
        target_system="OMH",
        message_type="XML_FILE",
        content_type="application/xml",
        payload_text="<root><heavy>xml_content</heavy></root>",
        payload_json={"heavy": "json"},
        payload_sha256="abc123sha256",
        payload_size_bytes=100,
        status=IntegrationMessageStatus.RECEIVED,
    )
    session.add(msg)
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        try:
            resp = await client.get("/api/onec/xml/messages?limit=10")
            assert resp.status_code == 200
            items = resp.json()
            assert len(items) >= 1
            item = next(m for m in items if m["id"] == str(msg.id))
            assert "payload_text" not in item
            assert "payload_json" not in item
            assert item["source_system"] == "1C_ERP"

            detail_resp = await client.get(f"/api/onec/xml/messages/{msg.id}")
            assert detail_resp.status_code == 200
            detail = detail_resp.json()
            assert detail["payload_text"] == "<root><heavy>xml_content</heavy></root>"
            assert detail["payload_json"] == {"heavy": "json"}
        finally:
            app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_printing_lines_pagination_and_recalculation(session):
    await ensure_package(session, "omh-package-printer", "Printing Package")

    printer = PrintPrinter(
        name="Zebra ZT410",
        dpi=203,
        connector_id=uuid4(),
    )
    session.add(printer)
    await session.flush()

    job = PrintJob(
        job_key=f"JOB-{uuid4().hex[:8]}",
        printer_id=printer.id,
        source_system="1C_ERP",
        status=PrintJobStatus.PRINTING,
    )
    session.add(job)
    await session.flush()

    # Create exactly 120 lines as specified in Section 6.7
    for i in range(120):
        code = f"010460000000000021{i:06d}"
        zpl = f"^XA^FD{i}^FS^XZ"
        line = PrintJobLine(
            job_id=job.id,
            sequence_no=i + 1,
            code=code,
            code_visible=code,
            code_sha256=f"sha_{i}",
            zpl=zpl,
            zpl_sha256=f"zpl_{i}",
            status=PrintLineStatus.PRINTED if i < 100 else PrintLineStatus.ERROR,
        )
        session.add(line)
    await session.commit()

    # 1. Test full recalculation over all 120 lines
    await _recalculate_job(session, job)
    assert job.total_lines == 120
    assert job.printed_lines == 100
    assert job.error_lines == 20

    # 2. Test paginated user retrieval
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        try:
            p1 = await client.get(f"/api/printing/jobs/{job.id}/lines?limit=50&offset=0")
            assert p1.status_code == 200
            lines_p1 = p1.json()
            assert len(lines_p1) == 50
            assert lines_p1[0]["sequence_no"] == 1

            p3 = await client.get(f"/api/printing/jobs/{job.id}/lines?limit=50&offset=100")
            assert p3.status_code == 200
            lines_p3 = p3.json()
            assert len(lines_p3) == 20
            assert lines_p3[-1]["sequence_no"] == 120
        finally:
            app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_production_exports_filtered_by_type(session):
    r1 = BackupRecord(
        backup_type=BackupType.DATABASE_DUMP,
        status=BackupStatus.SUCCESS,
        size_bytes=1024 * 1024,
    )
    r2 = BackupRecord(
        backup_type=BackupType.CONFIG_EXPORT,
        status=BackupStatus.SUCCESS,
        size_bytes=4096,
    )
    session.add_all([r1, r2])
    await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        try:
            resp_db = await client.get("/api/production/exports?backup_type=database_dump")
            assert resp_db.status_code == 200
            items_db = resp_db.json()
            assert any(item["id"] == str(r1.id) for item in items_db)
            assert not any(item["id"] == str(r2.id) for item in items_db)

            resp_all = await client.get("/api/production/exports")
            assert resp_all.status_code == 200
            items_all = resp_all.json()
            assert any(item["id"] == str(r1.id) for item in items_all)
            assert any(item["id"] == str(r2.id) for item in items_all)
        finally:
            app.dependency_overrides.pop(get_session, None)
