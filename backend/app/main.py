from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.artifacts.router import router as artifacts_router
from app.core.config import get_settings
from app.connectors.router import router as connectors_router
from app.core.errors import BadRequestError, NotFoundError
from app.demo.router import router as demo_router
from app.events.router import router as events_router
from app.execution.router import router as execution_router
from app.health.router import router as health_router
from app.incidents.router import router as incidents_router
from app.mappings.router import router as mappings_router
from app.maintenance.router import router as maintenance_router
from app.mocks.onec_http_service import router as mock_onec_router
from app.notifications.router import router as notifications_router
from app.onec_workbench.router import router as onec_workbench_router
from app.onec_scenarios.router import router as onec_scenarios_router
from app.onec_templates.router import router as onec_templates_router
from app.operation_templates.router import router as operation_templates_router
from app.polling.router import router as polling_router
from app.printing.router import router as printing_router
from app.retention.router import router as retention_router
from app.replay.router import router as replay_router
from app.workflows.router import router as workflows_router

app = FastAPI(title="Open Manufacturing Hub")
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
app.include_router(demo_router)
app.include_router(connectors_router)
app.include_router(mappings_router)
app.include_router(workflows_router)
app.include_router(execution_router)
app.include_router(artifacts_router)
app.include_router(replay_router)
app.include_router(health_router)
app.include_router(incidents_router)
app.include_router(notifications_router)
app.include_router(maintenance_router)
app.include_router(retention_router)
app.include_router(polling_router)
app.include_router(printing_router)
app.include_router(onec_workbench_router)
app.include_router(onec_scenarios_router)
app.include_router(onec_templates_router)
app.include_router(operation_templates_router)
app.include_router(mock_onec_router)
