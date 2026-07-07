from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.flow_builder.preview import preview_builder
from app.odata_master.compiler import compile_wizard_spec
from app.odata_master.schemas import ODataWizardSpec


async def preview_wizard(session: AsyncSession, spec: ODataWizardSpec, *, run_real_queries: bool = False) -> dict[str, Any]:
    compiled = compile_wizard_spec(spec)
    sample = compiled["flow_payload"].get("test_payload_json") or {}
    preview = await preview_builder(session, compiled["builder_json"], sample, run_real_queries=run_real_queries)
    return {**compiled, "preview": preview}
