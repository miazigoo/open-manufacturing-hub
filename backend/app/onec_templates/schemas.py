from typing import Any

from pydantic import BaseModel


class OneCHTTPTemplateRead(BaseModel):
    endpoints: list[dict[str, str]]
    request_envelope: dict[str, Any]
    success_response: dict[str, Any]
    failure_response: dict[str, Any]
    pseudo_code: str
