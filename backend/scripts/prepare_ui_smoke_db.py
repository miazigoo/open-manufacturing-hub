from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select

from app.artifacts.models import Artifact  # noqa: F401
from app.audit.models import AuditEvent  # noqa: F401
from app.business_rules.models import BusinessRuleSet  # noqa: F401
from app.config_versions.models import ConfigVersion  # noqa: F401
from app.connectors.models import ConnectorInstance
from app.core.database import Base, async_session, engine
from app.core.enums import ConnectorDirection, ConnectorInstanceStatus
from app.enterprise_runtime.models import (
    BusinessRuleDefinition,
    CanonicalBusinessObject,
    DeadLetterQueueItem,
    IntegrationQueueMessage,
    ODataCacheEntry,
    QueueAttempt,
    ResolverDefinition,
)  # noqa: F401
from app.events.models import EventRun, EventStep, IntegrationEvent  # noqa: F401
from app.execution.registry import registry
from app.external_errors.models import ExternalErrorRecord  # noqa: F401
from app.health.models import AgentHeartbeat, HealthCheck, Site  # noqa: F401
from app.incidents.models import Incident, IncidentEvent  # noqa: F401
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute, ODataLookupTemplate  # noqa: F401
from app.integration_flows.models import IntegrationFlow  # noqa: F401
from app.maintenance.models import MaintenanceWindow  # noqa: F401
from app.mappings.models import MappingDefinition, MappingVersion  # noqa: F401
from app.notifications.models import NotificationDelivery, NotificationRule  # noqa: F401
from app.onboarding.models import OnboardingState  # noqa: F401
from app.onec_workbench.models import IntegrationMessage  # noqa: F401
from app.operation_templates.models import OperationTemplate  # noqa: F401
from app.packages.models import InstalledPackage  # noqa: F401
from app.packages_auth.models import AuthRecoveryKey, AuthSession, AuthSettings, AuthUser  # noqa: F401
from app.polling.models import PollingJob, PollingJobRun, SourceEventCursor  # noqa: F401
from app.printing.models import PrintJob, PrintJobLine, PrintJobLog, PrintPrinter  # noqa: F401
from app.production.models import BackupRecord, ProductionState  # noqa: F401
from app.resolvers.models import ResolverCacheEntry, ResolverDefinitionV2  # noqa: F401
from app.test_console.models import SavedTestCase  # noqa: F401
from app.workflows.models import Workflow  # noqa: F401


async def upsert_connector(name: str, connector_type: str, direction: ConnectorDirection, config_json: dict[str, Any]) -> None:
    async with async_session() as session:
        existing = (await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == name))).scalar_one_or_none()
        if existing is None:
            existing = ConnectorInstance(name=name, connector_type=connector_type, direction=direction)
            session.add(existing)
        existing.enabled = True
        existing.status = ConnectorInstanceStatus.ENABLED
        existing.config_json = config_json
        await session.commit()


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    await upsert_connector(
        "Mock WMS",
        "mock_wms",
        ConnectorDirection.TARGET,
        {"fail_warehouse_ids": ["005"], "success_warehouse_ids": ["MAIN"]},
    )
    await upsert_connector(
        "DNP Service",
        "rest",
        ConnectorDirection.TARGET,
        {
            "method": "POST",
            "url": "https://dnp.example.local/api/marking/pools",
            "headers": {},
            "timeout_seconds": 3,
            "mock_response_json": {"accepted": True, "external_document_id": "DNP-POOL-001"},
        },
    )
    await upsert_connector(
        "1C ERP",
        "onec",
        ConnectorDirection.BIDIRECTIONAL,
        {
            "base_url": "https://onec.example.local/odata/standard.odata",
            "auth": {"type": "none"},
            "mock_odata": {
                "Catalog_Контрагенты": [
                    {"Ref_Key": "customer-001", "ИНН": "1234567890", "Description": "ООО Тест"},
                    {"Ref_Key": "customer-002", "ИНН": "7701000000", "Description": "ООО Резерв"},
                ],
                "Catalog_Номенклатура": [
                    {"Ref_Key": "product-abc", "Артикул": "ABC-123", "Description": "Product ABC"},
                ],
            },
        },
    )

    print(f"Prepared UI smoke database with {len(registry.list())} registered execution steps")


if __name__ == "__main__":
    asyncio.run(main())
