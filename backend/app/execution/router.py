from pydantic import BaseModel
from fastapi import APIRouter

from app.execution.registry import registry

router = APIRouter(tags=["execution"])


class StepMetadataRead(BaseModel):
    name: str
    display_name: str


@router.get("/api/execution/steps", response_model=list[StepMetadataRead])
async def execution_steps():
    return registry.list()
