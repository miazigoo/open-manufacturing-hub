import httpx

from app.connectors.builtin.onec.client import OneCHTTPClient
from app.connectors.builtin.onec_connector import OneCConnector
from app.connectors.registry import registry
from app.sdk.types import ConnectorContext


ONEC_CONFIG = {
    "base_url": "https://onec.example.local/odata/standard.odata",
    "http_service_base_url": "https://onec.example.local/hs/omh",
    "auth": {"type": "basic", "username": "api", "password": "secret"},
    "timeout_seconds": 10,
    "verify_ssl": True,
    "odata": {"enabled": True, "default_page_size": 1, "max_pages": 3},
    "http_services": {"enabled": True},
}


async def test_onec_connector_registered_and_validates_config():
    assert registry.get("onec").display_name == "1C Connector"
    connector = OneCConnector()
    valid = await connector.validate_config(ONEC_CONFIG)
    assert valid.valid is True
    assert valid.warnings

    missing_url = await connector.validate_config({"auth": {"type": "none"}})
    assert missing_url.valid is False
    assert "base_url or http_service_base_url is required" in missing_url.errors

    invalid_auth = await connector.validate_config({"base_url": "https://onec.example.local", "auth": {"type": "oauth"}})
    assert invalid_auth.valid is False
    assert "auth.type must be none or basic" in invalid_auth.errors

    invalid_paging = await connector.validate_config({"base_url": "https://onec.example.local", "odata": {"default_page_size": "bad"}})
    assert invalid_paging.valid is False
    assert "odata.default_page_size must be positive" in invalid_paging.errors


async def test_onec_config_is_masked_in_connector_api(client):
    response = await client.post(
        "/api/connectors",
        json={"name": "1C ERP", "connector_type": "onec", "direction": "bidirectional", "config_json": ONEC_CONFIG},
    )
    assert response.status_code == 200
    connector = response.json()
    assert connector["config_json"]["auth"]["password"] == "***"


async def test_onec_odata_read_paginates_and_manual_endpoint(monkeypatch, client):
    calls = []

    async def fake_request(self, method, url, *, params=None, json_payload=None, headers=None):
        calls.append({"method": method, "url": url, "params": params, "json_payload": json_payload, "headers": headers})
        if len(calls) == 1:
            return httpx.Response(200, json={"value": [{"Ref_Key": "A", "Number": "SO-1"}], "@odata.nextLink": "https://onec.example.local/odata/standard.odata/Document_ЗаказКлиента?$skip=1"}), {"url": url, "params": params}, None, None
        if len(calls) == 2:
            return httpx.Response(200, json={"value": [{"Ref_Key": "B", "Number": "SO-2"}]}), {"url": url, "params": params}, None, None
        return httpx.Response(200, json={"value": []}), {"url": url, "params": params}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    created = await client.post(
        "/api/connectors",
        json={"name": "1C ERP", "connector_type": "onec", "direction": "bidirectional", "config_json": ONEC_CONFIG},
    )
    connector = created.json()
    response = await client.post(f"/api/connectors/{connector['id']}/onec/odata/read", json={"resource": "Document_ЗаказКлиента", "query": {"$top": 1}})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [item["Ref_Key"] for item in body["items"]] == ["A", "B"]
    assert calls[0]["params"] is None
    assert "$top=1" in calls[0]["url"]
    assert "$skip" not in calls[0]["url"]
    assert "$format=json" in calls[0]["url"]
    assert calls[0]["headers"]["Accept"] == "application/json"
    assert calls[1]["params"] is None


async def test_onec_odata_read_accepts_single_entity_response(monkeypatch, client):
    async def fake_request(self, method, url, *, params=None, json_payload=None, headers=None):
        return httpx.Response(
            200,
            json={
                "odata.metadata": "https://onec.example.local/odata/standard.odata/$metadata#Document_ЗаказКлиента/@Element",
                "Ref_Key": "doc-1",
                "Number": "SO-1",
            },
        ), {"url": url, "params": params}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    created = await client.post(
        "/api/connectors",
        json={"name": "1C ERP", "connector_type": "onec", "direction": "bidirectional", "config_json": ONEC_CONFIG},
    )
    connector = created.json()
    response = await client.post(f"/api/connectors/{connector['id']}/onec/odata/read", json={"resource": "Document_ЗаказКлиента(guid'doc-1')", "query": {"$top": 1}})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["items"][0]["Ref_Key"] == "doc-1"


async def test_onec_odata_read_preserves_resource_query(monkeypatch, client):
    calls = []

    async def fake_request(self, method, url, *, params=None, json_payload=None, headers=None):
        calls.append({"url": url, "params": params})
        return httpx.Response(200, json={"value": [{"Ref_Key": "doc-1"}]}), {"url": url, "params": params}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    created = await client.post(
        "/api/connectors",
        json={"name": "1C ERP", "connector_type": "onec", "direction": "bidirectional", "config_json": ONEC_CONFIG},
    )
    connector = created.json()
    response = await client.post(
        f"/api/connectors/{connector['id']}/onec/odata/read",
        json={"resource": "Document_ЗаказКлиента?$filter=Number eq 'SO-1'", "query": {"$top": 1, "$filter": "Number eq 'SO-2'"}},
    )
    assert response.status_code == 200
    assert calls[0]["params"] is None
    assert calls[0]["url"].count("$filter=") == 1
    assert "$filter=Number%20eq%20'SO-1'" in calls[0]["url"]
    assert "$top=1" in calls[0]["url"]


async def test_onec_send_and_dry_run_map_http_errors(monkeypatch):
    connector = OneCConnector()

    async def fake_request(self, method, url, *, params=None, json_payload=None):
        assert method == "POST"
        assert url.endswith("/shipment-orders")
        assert json_payload["payload"]["document"] == {"external_id": "SO-1"}
        return httpx.Response(500, json={"error": "failed"}), {"method": method, "url": url, "body": json_payload}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    result = await connector.send(
        ONEC_CONFIG,
        {"_omh": {"method": "POST", "path": "/shipment-orders"}, "document": {"external_id": "SO-1"}},
        ConnectorContext(),
    )
    assert result.success is False
    assert result.status_code == 500
    assert result.error_code == "ONEC_HTTP_SERVICE_ERROR"

    async def must_not_call(*args, **kwargs):
        raise AssertionError("dry-run must not call 1C")

    monkeypatch.setattr(OneCHTTPClient, "request", must_not_call)
    dry = await connector.dry_run_send(ONEC_CONFIG, {"_omh": {"method": "POST", "path": "/shipment-orders"}, "document": {}}, ConnectorContext(dry_run=True))
    assert dry.success is True
    assert dry.response_payload["dry_run"] is True
    assert dry.request_payload["body"]["payload"] == {"document": {}}


async def test_onec_healthcheck_uses_configured_http_health_path(monkeypatch):
    connector = OneCConnector()
    calls = []

    async def fake_request(self, method, url, *, params=None, json_payload=None):
        calls.append(url)
        return httpx.Response(200, json={"success": True, "status": "ok"}), {"url": url}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    result = await connector.healthcheck(
        {
            "http_service_base_url": "https://onec.example.local/hs/omh",
            "auth": {"type": "none"},
            "http_services": {"enabled": True, "services": [{"name": "health", "method": "GET", "path": "/health"}]},
        }
    )
    assert result.status == "ok"
    assert calls == ["https://onec.example.local/hs/omh/health"]


async def test_onec_business_response_handling(monkeypatch):
    connector = OneCConnector()

    async def success_response(self, method, url, *, params=None, json_payload=None):
        return httpx.Response(200, json={"success": True, "external_document_id": "1C-SHIP-1532"}), {"method": method, "url": url, "body": json_payload}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", success_response)
    ok = await connector.send(ONEC_CONFIG, {"_omh": {"operation": "update_shipment_status"}, "payload": {"external_order_id": "1532"}}, ConnectorContext())
    assert ok.success is True

    async def business_error(self, method, url, *, params=None, json_payload=None):
        return httpx.Response(200, json={"success": False, "error_code": "ORDER_NOT_FOUND", "error_message": "Order was not found"}), {"method": method, "url": url, "body": json_payload}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", business_error)
    failed = await connector.send(ONEC_CONFIG, {"_omh": {"operation": "update_shipment_status"}, "payload": {"external_order_id": "404"}}, ConnectorContext())
    assert failed.success is False
    assert failed.error_code == "ORDER_NOT_FOUND"

    async def invalid_json(self, method, url, *, params=None, json_payload=None):
        return httpx.Response(200, text="not json"), {"method": method, "url": url, "body": json_payload}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", invalid_json)
    invalid = await connector.send(ONEC_CONFIG, {"_omh": {"operation": "update_shipment_status"}, "payload": {"external_order_id": "1532"}}, ConnectorContext())
    assert invalid.success is False
    assert invalid.error_code == "ONEC_RESPONSE_INVALID"
