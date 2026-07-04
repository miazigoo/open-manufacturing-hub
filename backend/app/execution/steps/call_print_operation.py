from __future__ import annotations

from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.printing.schemas import OneCPrintBatchRequest
from app.printing.service import create_and_send_onec_batch


class CallPrintOperationStep:
    name = "call_print_operation"
    display_name = "Call Print Operation"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        payload = dict(context.variables.get("mapped_payload") or context.variables.get("payload") or {})
        try:
            request = OneCPrintBatchRequest.model_validate(payload)
        except Exception as exc:
            return StepResult.failed("PRINT_REQUEST_INVALID", str(exc), artifacts=[ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "print_request_error.json", {"error": str(exc), "payload": payload})])
        if context.dry_run:
            request.dry_run = True
        result = await create_and_send_onec_batch(context.session, request)
        response = {"job_id": str(result.job.id), "status": result.job.status.value, "processed": result.processed, "sent": result.sent, "failed": result.failed, "dry_run": result.dry_run}
        artifacts = [ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "print_request.json", payload), ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "print_response.json", response)]
        if result.failed:
            return StepResult.failed("PRINT_OPERATION_FAILED", f"{result.failed} print lines failed", artifacts=artifacts, variables_update={"response": {"status_code": 200, "body": response}})
        status = StepResult.dry_run if context.dry_run or result.dry_run else StepResult.success
        return status("Print operation complete", artifacts=artifacts, variables_update={"print_response": response, "response": {"status_code": 200, "body": response}})
