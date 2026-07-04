from __future__ import annotations

from typing import Any

from app.transforms.registry import registry
from app.transforms.schemas import TransformResult, TransformStep, TransformTraceItem


class TransformEngine:
    def apply_chain(self, value: Any, chain: list[dict[str, Any] | TransformStep], context: dict[str, Any] | None = None) -> TransformResult:
        context = context or {}
        current = value
        trace: list[TransformTraceItem] = []
        for raw_step in chain:
            step = raw_step if isinstance(raw_step, TransformStep) else TransformStep(**raw_step)
            item = registry.get(step.name)
            if item is None:
                return TransformResult(success=False, value=current, error_code="TRANSFORM_NOT_FOUND", error_message=f"Transform {step.name} not found", trace=trace)
            before = current
            try:
                current = item[1](current, step.args, context)
            except Exception as exc:
                return TransformResult(success=False, value=before, error_code="TRANSFORM_FAILED", error_message=str(exc) or exc.__class__.__name__, trace=trace)
            trace.append(TransformTraceItem(transform=step.name, before=before, after=current, args=step.args))
        return TransformResult(success=True, value=current, trace=trace)


engine = TransformEngine()
