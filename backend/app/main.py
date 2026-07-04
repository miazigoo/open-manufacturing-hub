from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.artifacts.router import router as artifacts_router
from app.core.database import async_session
from app.core.config import get_settings
from app.connectors.router import router as connectors_router
from app.core.errors import BadRequestError, NotFoundError
from app.demo.router import router as demo_router
from app.events.router import router as events_router
from app.enterprise_runtime.router import router as enterprise_runtime_router
from app.execution.router import router as execution_router
from app.external_errors.router import router as external_errors_router
from app.flow_builder.router import router as flow_builder_router
from app.health.router import router as health_router
from app.incidents.router import router as incidents_router
from app.integration_designer.router import router as integration_designer_router
from app.integration_bus.router import router as integration_bus_router
from app.integration_flows.router import router as integration_flows_router
from app.json_builder.router import router as json_builder_router
from app.mappings.router import router as mappings_router
from app.matchers.router import router as matchers_router
from app.maintenance.router import router as maintenance_router
from app.mocks.onec_http_service import router as mock_onec_router
from app.notifications.router import router as notifications_router
from app.onec_workbench.router import router as onec_workbench_router
from app.onec_scenarios.router import router as onec_scenarios_router
from app.onec_templates.router import router as onec_templates_router
from app.operation_templates.router import router as operation_templates_router
from app.odata_explorer.router import router as odata_explorer_router
from app.packages.router import router as packages_router
from app.plugin_store.router import router as plugin_store_router
from app.polling.router import router as polling_router
from app.printing.router import router as printing_router
from app.retention.router import router as retention_router
from app.replay.router import router as replay_router
from app.scenario_library.router import router as scenario_library_router
from app.test_console.router import router as test_console_router
from app.workflows.router import router as workflows_router
from app.xml_tools.router import router as xml_tools_router
from app.packages.service import startup_package_check


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with async_session() as session:
        await startup_package_check(session)
        await session.commit()
    yield


app = FastAPI(title="Open Manufacturing Hub", lifespan=lifespan)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(BadRequestError)
async def bad_request_handler(_: Request, exc: BadRequestError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


app.include_router(events_router)
app.include_router(enterprise_runtime_router)
app.include_router(demo_router)
app.include_router(connectors_router)
app.include_router(mappings_router)
app.include_router(workflows_router)
app.include_router(execution_router)
app.include_router(external_errors_router)
app.include_router(flow_builder_router)
app.include_router(artifacts_router)
app.include_router(replay_router)
app.include_router(health_router)
app.include_router(incidents_router)
app.include_router(integration_bus_router)
app.include_router(integration_flows_router)
app.include_router(json_builder_router)
app.include_router(integration_designer_router)
app.include_router(matchers_router)
app.include_router(scenario_library_router)
app.include_router(odata_explorer_router)
app.include_router(xml_tools_router)
app.include_router(test_console_router)
app.include_router(notifications_router)
app.include_router(packages_router)
app.include_router(plugin_store_router)
app.include_router(maintenance_router)
app.include_router(retention_router)
app.include_router(polling_router)
app.include_router(printing_router)
app.include_router(onec_workbench_router)
app.include_router(onec_scenarios_router)
app.include_router(onec_templates_router)
app.include_router(operation_templates_router)
app.include_router(mock_onec_router)
