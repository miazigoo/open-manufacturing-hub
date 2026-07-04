import os

os.environ["OMH_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

import pytest
from httpx import ASGITransport, AsyncClient

from app.artifacts.models import Artifact  # noqa: F401
from app.connectors.models import ConnectorInstance  # noqa: F401
from app.core.database import Base, async_session, engine
from app.events.models import EventRun, EventStep, IntegrationEvent  # noqa: F401
from app.external_errors.models import ExternalErrorRecord  # noqa: F401
from app.health.models import AgentHeartbeat, HealthCheck, Site  # noqa: F401
from app.incidents.models import Incident, IncidentEvent  # noqa: F401
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute, ODataLookupTemplate  # noqa: F401
from app.maintenance.models import MaintenanceWindow  # noqa: F401
from app.mappings.models import MappingDefinition, MappingVersion  # noqa: F401
from app.notifications.models import NotificationDelivery, NotificationRule  # noqa: F401
from app.onec_workbench.models import IntegrationMessage  # noqa: F401
from app.operation_templates.models import OperationTemplate  # noqa: F401
from app.polling.models import PollingJob, PollingJobRun, SourceEventCursor  # noqa: F401
from app.printing.models import PrintJob, PrintJobLine, PrintJobLog, PrintPrinter  # noqa: F401
from app.test_console.models import SavedTestCase  # noqa: F401
from app.workflows.models import Workflow  # noqa: F401
from app.main import app


@pytest.fixture(autouse=True)
async def database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        session.add(
            ConnectorInstance(
                name="Mock WMS",
                connector_type="mock_wms",
                direction="target",
                enabled=True,
                status="enabled",
                config_json={"fail_warehouse_ids": ["005"], "success_warehouse_ids": ["MAIN"]},
            )
        )
        await session.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def failed_payload():
    return {
        "source_system": "Mock ERP",
        "target_system": "Mock WMS",
        "event_type": "SalesOrderCreated",
        "entity_type": "SalesOrder",
        "entity_id": "1532",
        "payload": {"order_id": "1532", "warehouse_id": "005", "items": [{"sku": "ABC123", "qty": 5}]},
    }


@pytest.fixture
def success_payload(failed_payload):
    payload = dict(failed_payload)
    payload["payload"] = dict(failed_payload["payload"])
    payload["payload"]["warehouse_id"] = "MAIN"
    return payload
