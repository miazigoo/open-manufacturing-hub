from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.core.database import async_session
from app.core.enums import ConnectorDirection, ConnectorInstanceStatus, EnterpriseQueueStatus, SecretType
from app.enterprise_runtime.models import DeadLetterQueueItem, IntegrationQueueMessage
from app.events.schemas import EventCreate
from app.events.service import create_event
from app.integration_bus import service as bus_service
from app.integration_flows import service as flow_service
from app.onec_scenarios.service import install_bidirectional_demo, install_erp_wms_integration, install_sales_order_demo
from app.packages.installer import PackageInstaller
from app.production import service as production_service
from app.production.schemas import ExportConfigRequest
from app.scenario_library.schemas import ScenarioInstallRequest
from app.scenario_library.service import install_scenario
from app.secrets import repository as secret_repository
from app.secrets.schemas import SecretCreate
from app.secrets.service import create_secret

RELEASE_PREFIX = "Release Fixture"


async def upsert_connector(session: AsyncSession, *, name: str, connector_type: str, direction: ConnectorDirection, config_json: dict[str, Any]) -> ConnectorInstance:
    item = (await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == name))).scalar_one_or_none()
    if item is None:
        item = ConnectorInstance(name=name, connector_type=connector_type, direction=direction)
        session.add(item)
    item.enabled = True
    item.status = ConnectorInstanceStatus.ENABLED
    item.config_json = config_json
    await session.flush()
    return item


async def ensure_secret(session: AsyncSession, name: str, value: str, secret_type: SecretType) -> None:
    existing = await secret_repository.get_by_name(session, name)
    if existing is not None:
        existing.enabled = True
        await session.flush()
        return
    await create_secret(session, SecretCreate(name=name, value=value, secret_type=secret_type, description=f"{RELEASE_PREFIX} secret"), actor="release-fixtures")


async def install_packages(session: AsyncSession) -> None:
    installer = PackageInstaller()
    for package_id, demo in (("omh-package-onec", True), ("omh-package-printer", False)):
        await installer.install_package(session, package_id, install_demo_data=demo)
    if os.getenv("RELEASE_FIXTURES_ENABLE_AUTH", "0") == "1":
        await installer.install_package(session, "omh-package-auth", install_demo_data=False)


async def install_connectors(session: AsyncSession) -> dict[str, ConnectorInstance]:
    connectors = {}
    connectors["erp"] = await upsert_connector(
        session,
        name="Demo 1C ERP",
        connector_type="onec",
        direction=ConnectorDirection.BIDIRECTIONAL,
        config_json={
            "base_url": "https://onec.example.local/odata/standard.odata",
            "http_service_base_url": "https://onec.example.local/hs/omh",
            "auth": {"type": "basic", "username": "release", "password": {"$secret": "release.onec.password"}},
            "mock_odata": {
                "Catalog_Контрагенты": [{"Ref_Key": "customer-001", "ИНН": "1234567890", "Description": "ООО Release Customer"}],
                "Catalog_Номенклатура": [{"Ref_Key": "product-abc-123", "Артикул": "ABC-123", "Description": "Release Product ABC-123"}],
            },
            "operations": {"receive_upd_xml": {"method": "POST", "path": "/xml/inbound", "content_type": "application/xml", "body_mode": "raw_xml"}},
        },
    )
    connectors["wms"] = await upsert_connector(
        session,
        name="Demo 1C WMS",
        connector_type="onec",
        direction=ConnectorDirection.BIDIRECTIONAL,
        config_json={"http_service_base_url": "https://wms-onec.example.local/hs/omh", "auth": {"type": "none"}},
    )
    dnp_config = {"method": "POST", "url": os.getenv("RELEASE_FIXTURE_DNP_URL", "http://127.0.0.1:8000/api/mock-onec/hs/omh/stock-balances"), "headers": {"Authorization": {"$secret": "release.dnp.api_token"}}, "timeout_seconds": 5, "mock_response_json": {"accepted": True, "external_document_id": "DNP-POOL-001"}}
    connectors["dnp"] = await upsert_connector(
        session,
        name="DNP Service",
        connector_type="rest",
        direction=ConnectorDirection.TARGET,
        config_json=dnp_config,
    )
    connectors["dnp_alias"] = await upsert_connector(
        session,
        name="DNP REST Service",
        connector_type="rest",
        direction=ConnectorDirection.TARGET,
        config_json=dnp_config,
    )
    connectors["zebra"] = await upsert_connector(
        session,
        name="Zebra Production",
        connector_type="zpl_printer",
        direction=ConnectorDirection.TARGET,
        config_json={"printer_name": "Zebra Production", "host": "127.0.0.1", "port": 9100, "dpi": 203, "timeout_seconds": 2},
    )
    connectors["mock_wms"] = await upsert_connector(
        session,
        name="Mock WMS",
        connector_type="mock_wms",
        direction=ConnectorDirection.TARGET,
        config_json={"fail_warehouse_ids": ["005"], "success_warehouse_ids": ["MAIN"]},
    )
    return connectors


async def install_release_flows(session: AsyncSession) -> None:
    await bus_service.install_presets(session)
    await flow_service.install_marking_pool_preset(session)
    await flow_service.install_two_odata_to_endpoint_preset(session)
    for code, slug in (
        ("onec_xml_raw_bridge", "release-upd-xml-raw"),
        ("onec_xml_odata_lookup", "release-upd-inn-lookup"),
        ("onec_to_printer", "release-print-zpl"),
        ("api_to_onec", "release-api-to-onec"),
    ):
        await install_scenario(session, code, ScenarioInstallRequest(endpoint_slug=slug))
    await install_sales_order_demo(session)
    await install_bidirectional_demo(session)
    await install_erp_wms_integration(session)


async def create_expected_events(session: AsyncSession) -> None:
    existing = (await session.execute(select(IntegrationQueueMessage).where(IntegrationQueueMessage.business_key == "release-retry-001"))).scalar_one_or_none()
    if existing is None:
        event = await create_event(session, EventCreate(correlation_id="release-success-001", source_system="Release Fixtures", target_system="Mock WMS", event_type="ReleaseSuccess", entity_type="ReleaseOrder", entity_id="release-success-001", payload={"order_id": "release-success-001", "warehouse_id": "MAIN", "items": [{"sku": "ABC-123", "qty": 1}]}))
        retry = IntegrationQueueMessage(event_id=event.id, business_object="ReleaseOrder", business_key="release-retry-001", operation="retry_to_success", status=EnterpriseQueueStatus.RETRY_WAITING, attempts=1, max_attempts=3, payload_json={"order_id": "release-retry-001"}, original_payload_json={"order_id": "release-retry-001"}, last_error_code="REST_TEMPORARY_FAILURE", last_error_message="First target call failed")
        session.add(retry)
        dlq = DeadLetterQueueItem(event_id=event.id, business_object="ReleaseOrder", operation="printer_unavailable", reason="Printer unavailable during release fixture", payload_json={"job_key": "release-print-error"}, current_payload_json={"job_key": "release-print-error"}, last_error="PRINTER_UNAVAILABLE", attempts=3)
        session.add(dlq)
        await session.flush()


async def main() -> None:
    async with async_session() as session:
        await install_packages(session)
        await ensure_secret(session, "release.onec.password", "release-onec-password", SecretType.PASSWORD)
        await ensure_secret(session, "release.dnp.api_token", "release-dnp-token", SecretType.API_TOKEN)
        connectors = await install_connectors(session)
        await install_release_flows(session)
        await create_expected_events(session)
        await production_service.export_config(session, ExportConfigRequest(secrets_policy="masked", created_by="release-fixtures"))
        await session.commit()
        print(
            {
                "status": "ok",
                "connectors": sorted(connector.name for connector in connectors.values()),
                "seeded_at": datetime.now(timezone.utc).isoformat(),
            }
        )


if __name__ == "__main__":
    asyncio.run(main())
