"""Ozon Seller API client (async, typed for the OMH integration scope).

See docs/integrations/ozon-api-map.md for the endpoint map used here.
"""
from __future__ import annotations

from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api-seller.ozon.ru"
DEFAULT_TIMEOUT_SECONDS = 30.0


class OzonError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class OzonClient:
    def __init__(self, *, client_id: str, api_key: str, base_url: str = DEFAULT_BASE_URL, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS):
        if not client_id or not api_key:
            raise OzonError("Ozon: заполните Client-Id и Api-Key в коннекторе (или secret reference).")
        self.base_url = base_url.rstrip("/") or DEFAULT_BASE_URL
        self.headers = {
            "Client-Id": client_id,
            "Api-Key": api_key,
            "Content-Type": "application/json",
        }
        self.timeout = timeout_seconds

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}{path}", json=body, headers=self.headers)
        except httpx.HTTPError as exc:
            raise OzonError(f"Ozon недоступен: {exc}") from exc
        if response.status_code == 429:
            raise OzonError("Ozon rate limit (429): уменьшите частоту синхронизации.", status_code=429)
        if response.status_code == 401 or response.status_code == 403:
            raise OzonError(f"Ozon отклонил ключ (HTTP {response.status_code}): проверьте Client-Id/Api-Key и роль ключа.", status_code=response.status_code)
        if response.status_code >= 400:
            raise OzonError(f"Ozon вернул HTTP {response.status_code}: {response.text[:500]}", status_code=response.status_code)
        try:
            return response.json()
        except ValueError as exc:
            raise OzonError(f"Ozon вернул не-JSON ответ: {response.text[:300]}") from exc

    # --- catalog ---

    async def list_products(self, *, visibility: str = "ALL", limit: int = 1000, last_id: str = "") -> dict[str, Any]:
        body: dict[str, Any] = {"filter": {"visibility": visibility}, "limit": min(limit, 1000)}
        if last_id:
            body["last_id"] = last_id
        return await self._post("/v3/product/list", body)

    async def product_info_list(self, *, offer_ids: list[str] | None = None, product_ids: list[int] | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if offer_ids:
            body["offer_id"] = offer_ids
        if product_ids:
            body["product_id"] = product_ids
        return await self._post("/v3/product/info/list", body)

    # --- stocks ---

    async def get_stocks(self, *, offer_ids: list[str] | None = None, product_ids: list[int] | None = None, visibility: str = "ALL", limit: int = 1000, cursor: str = "") -> dict[str, Any]:
        body: dict[str, Any] = {"filter": {"visibility": visibility}, "limit": min(limit, 1000)}
        if offer_ids:
            body["filter"]["offer_id"] = offer_ids
        if product_ids:
            body["filter"]["product_id"] = product_ids
        if cursor:
            body["cursor"] = cursor
        return await self._post("/v4/product/info/stocks", body)

    async def update_stocks(self, stocks: list[dict[str, Any]]) -> dict[str, Any]:
        if not stocks:
            raise OzonError("Ozon update_stocks: пустой список stocks.")
        if len(stocks) > 100:
            raise OzonError("Ozon update_stocks: максимум 100 позиций за запрос (разбейте на пачки).")
        return await self._post("/v2/products/stocks", {"stocks": stocks})

    # --- prices ---

    async def update_prices(self, prices: list[dict[str, Any]]) -> dict[str, Any]:
        if not prices:
            raise OzonError("Ozon update_prices: пустой список prices.")
        if len(prices) > 1000:
            raise OzonError("Ozon update_prices: максимум 1000 позиций за запрос.")
        return await self._post("/v1/product/import/prices", {"prices": prices})

    async def get_prices(self, *, offer_ids: list[str] | None = None, product_ids: list[int] | None = None, visibility: str = "ALL", limit: int = 1000, cursor: str = "") -> dict[str, Any]:
        body: dict[str, Any] = {"filter": {"visibility": visibility}, "limit": min(limit, 1000)}
        if offer_ids:
            body["filter"]["offer_id"] = offer_ids
        if product_ids:
            body["filter"]["product_id"] = product_ids
        if cursor:
            body["cursor"] = cursor
        return await self._post("/v5/product/info/prices", body)

    # --- orders (FBS postings) ---

    async def list_fbs_orders(
        self,
        *,
        since: str,
        to: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
        with_analytics: bool = True,
        with_barcodes: bool = False,
        direction: str = "ASC",
    ) -> dict[str, Any]:
        filter_body: dict[str, Any] = {"since": since}
        if to:
            filter_body["to"] = to
        if status:
            filter_body["status"] = status
        body: dict[str, Any] = {
            "dir": direction,
            "filter": filter_body,
            "limit": min(limit, 100),
            "offset": offset,
            "with": {"analytics_data": with_analytics, "barcodes": with_barcodes},
        }
        return await self._post("/v3/posting/fbs/list", body)

    async def get_fbs_order(self, posting_number: str, *, with_analytics: bool = True) -> dict[str, Any]:
        return await self._post("/v3/posting/fbs/get", {"posting_number": posting_number, "with": {"analytics_data": with_analytics}})

    # --- warehouses ---

    async def list_warehouses(self) -> dict[str, Any]:
        return await self._post("/v1/warehouse/list", {})
