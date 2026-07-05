from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.artifacts.router import router as artifacts_router
from app.audit.middleware import request_id_middleware
from app.audit.router import router as audit_router
from app.business_rules.router import router as business_rules_router
from app.business_objects.router import router as business_objects_router
from app.core.database import async_session
from app.core.access import optional_auth_guard
from app.core.config import get_settings
from app.connectors.router import router as connectors_router
from app.change_sets.router import router as change_sets_router
from app.config_versions.router import router as config_versions_router
from app.core.errors import BadRequestError, NotFoundError
from app.demo.router import router as demo_router
from app.docs_portal.router import router as docs_portal_router
from app.docs_examples.router import router as docs_examples_router
from app.events.router import router as events_router
from app.environments.router import router as environments_router
from app.enterprise_runtime.router import dlq_router, queue_router, router as enterprise_runtime_router
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
from app.onboarding.router import router as onboarding_router
from app.operation_templates.router import router as operation_templates_router
from app.odata_connections.router import router as odata_connections_router
from app.odata_explorer.router import router as odata_explorer_router
from app.packages.router import router as packages_router
from app.packages.errors import PackageNotInstallableError
from app.packages.runtime import PackageAccessError, require_package_enabled
from app.plugin_store.router import router as plugin_store_router
from app.polling.router import router as polling_router
from app.printing.router import router as printing_router
from app.retention.router import router as retention_router
from app.replay.router import router as replay_router
from app.scenario_library.router import router as scenario_library_router
from app.resolvers.router import router as resolvers_router
from app.secrets.router import router as secrets_router
from app.test_console.router import router as test_console_router
from app.transforms.router import router as transforms_router
from app.ui.router import router as ui_router
from app.workflows.router import router as workflows_router
from app.xml_tools.router import router as xml_tools_router
from app.packages.service import startup_package_check
from app.production.startup import log_startup_banner
from app.packages_onec.router import router as packages_onec_router
from app.packages_printer.router import router as packages_printer_router
from app.packages_auth.router import router as auth_router
from app.packages_training.router import router as training_router
from app.production.router import router as production_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with async_session() as session:
        await log_startup_banner(session)
        await startup_package_check(session)
        await session.commit()
    yield


app = FastAPI(title="Open Manufacturing Hub", lifespan=lifespan)
app.middleware("http")(request_id_middleware)
app.middleware("http")(optional_auth_guard)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()],
    allow_origin_regex=settings.cors_allow_origin_regex,
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


@app.exception_handler(PackageAccessError)
async def package_access_handler(_: Request, exc: PackageAccessError):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.error, "package_id": exc.package_id, "message": exc.message})


@app.exception_handler(PackageNotInstallableError)
async def package_not_installable_handler(_: Request, exc: PackageNotInstallableError):
    return JSONResponse(status_code=400, content={"error": "PACKAGE_NOT_INSTALLABLE", "package_id": exc.package_id, "status": exc.status, "message": exc.message})


app.include_router(events_router)
app.include_router(business_objects_router)
app.include_router(business_rules_router)
app.include_router(resolvers_router)
app.include_router(transforms_router)
app.include_router(enterprise_runtime_router)
app.include_router(queue_router)
app.include_router(dlq_router)
app.include_router(demo_router)
app.include_router(connectors_router)
app.include_router(config_versions_router)
app.include_router(environments_router)
app.include_router(change_sets_router)
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
app.include_router(odata_connections_router, dependencies=[Depends(require_package_enabled("omh-package-onec"))])
app.include_router(odata_explorer_router, dependencies=[Depends(require_package_enabled("omh-package-onec"))])
app.include_router(xml_tools_router)
app.include_router(test_console_router)
app.include_router(docs_portal_router)
app.include_router(docs_examples_router)
app.include_router(ui_router)
app.include_router(notifications_router)
app.include_router(auth_router)
app.include_router(secrets_router, dependencies=[Depends(require_package_enabled("omh-package-secrets"))])
app.include_router(production_router)
app.include_router(audit_router)
app.include_router(packages_router)
app.include_router(packages_onec_router, dependencies=[Depends(require_package_enabled("omh-package-onec"))])
app.include_router(packages_printer_router, dependencies=[Depends(require_package_enabled("omh-package-printer"))])
app.include_router(training_router)
app.include_router(plugin_store_router)
app.include_router(maintenance_router)
app.include_router(retention_router)
app.include_router(polling_router)
app.include_router(printing_router, dependencies=[Depends(require_package_enabled("omh-package-printer"))])
app.include_router(onec_workbench_router, dependencies=[Depends(require_package_enabled("omh-package-onec"))])
app.include_router(onec_scenarios_router, dependencies=[Depends(require_package_enabled("omh-package-onec"))])
app.include_router(onec_templates_router, dependencies=[Depends(require_package_enabled("omh-package-onec"))])
app.include_router(operation_templates_router)
app.include_router(onboarding_router)
app.include_router(mock_onec_router)
