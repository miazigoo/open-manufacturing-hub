from __future__ import annotations

from typing import Any

from app.connectors.builtin.onec import errors
from app.connectors.builtin.onec.client import OneCHTTPClient, join_url, response_json
from app.connectors.builtin.onec.pagination import max_pages, pagination_params
from app.connectors.builtin.onec.schemas import OneCReadResult


async def read_odata(config: dict[str, Any], resource: str, query: dict[str, Any] | None = None) -> OneCReadResult:
    client = OneCHTTPClient(config)
    base_url = str(config.get("base_url") or "")
    items: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []
    next_url: str | None = None
    for page in range(max_pages(config)):
        url = next_url or join_url(base_url, resource)
        params = None if next_url else pagination_params(config, query, page)
        response, request_payload, error_code, error_message = await client.request("GET", url, params=params)
        requests.append(request_payload)
        if error_code:
            return OneCReadResult(False, request_payload={"requests": requests}, error_code=error_code, error_message=error_message)
        assert response is not None
        data, text = response_json(response)
        response_payload = {"status_code": response.status_code, "body": data if data is not None else {"text": text}}
        responses.append(response_payload)
        if response.status_code == 401:
            return OneCReadResult(False, request_payload={"requests": requests}, response_payload={"responses": responses}, error_code=errors.ONEC_AUTH_FAILED, error_message="1C authentication failed")
        if response.status_code >= 400:
            return OneCReadResult(False, request_payload={"requests": requests}, response_payload={"responses": responses}, error_code=errors.ONEC_ODATA_ERROR, error_message=f"1C OData returned {response.status_code}")
        if not isinstance(data, dict):
            return OneCReadResult(False, request_payload={"requests": requests}, response_payload={"responses": responses}, error_code=errors.ONEC_RESPONSE_INVALID, error_message="1C OData response is not a JSON object")
        page_items = data.get("value") if "value" in data else data.get("items")
        if not isinstance(page_items, list):
            return OneCReadResult(False, request_payload={"requests": requests}, response_payload={"responses": responses}, error_code=errors.ONEC_RESPONSE_INVALID, error_message="1C OData response does not contain value array")
        items.extend([item for item in page_items if isinstance(item, dict)])
        next_url = data.get("@odata.nextLink") if isinstance(data.get("@odata.nextLink"), str) else None
        requested_top = int((params or query or {}).get("$top") or 0)
        if next_url is None and (requested_top <= 0 or len(page_items) < requested_top):
            break
    return OneCReadResult(True, items=items, count=len(items), request_payload={"requests": requests}, response_payload={"responses": responses})
