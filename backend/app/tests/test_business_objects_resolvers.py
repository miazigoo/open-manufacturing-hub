from app.connectors.models import ConnectorInstance
from app.core.database import async_session


async def test_business_object_registry_api(client):
    response = await client.get("/api/business-objects")
    assert response.status_code == 200, response.text
    object_types = {item["object_type"] for item in response.json()}
    assert {"Customer", "Product", "Warehouse", "SalesOrder", "PrintJob"} <= object_types

    customer = await client.get("/api/business-objects/Customer")
    assert customer.status_code == 200
    assert "inn" in {field["name"] for field in customer.json()["fields"]}
    assert "uuid" in customer.json()["identity_fields"]


async def test_static_map_resolver_and_cache_hit(client):
    created = await client.post(
        "/api/resolvers",
        json={
            "name": "Resolve Customer Test",
            "resolver_code": "test_customer_static",
            "object_type": "Customer",
            "strategy": "static_map",
            "input_schema_json": {"anyOf": ["inn"]},
            "config_json": {"cache_key_fields": ["inn"], "entries": [{"match": {"inn": "123"}, "object": {"uuid": "cust-123", "inn": "123", "name": "ACME"}}]},
            "cache_enabled": True,
            "cache_ttl_seconds": 120,
        },
    )
    assert created.status_code == 200, created.text
    resolver_id = created.json()["id"]

    first = await client.post(f"/api/resolvers/{resolver_id}/resolve", json={"input": {"inn": "123"}})
    assert first.status_code == 200, first.text
    assert first.json()["success"] is True
    assert first.json()["object_json"]["uuid"] == "cust-123"
    assert first.json()["cache_status"] == "stored"

    second = await client.post("/api/resolvers/code/test_customer_static/resolve", json={"input": {"inn": "123"}})
    assert second.status_code == 200, second.text
    assert second.json()["cache_status"] == "hit"
    assert second.json()["object_json"]["object_type"] == "Customer"

    cache = await client.get("/api/resolvers/cache?resolver_code=test_customer_static")
    assert cache.status_code == 200
    assert cache.json()[0]["hit_count"] >= 1


async def test_odata_and_rest_resolver_strategies(client):
    async with async_session() as session:
        connector = ConnectorInstance(
            name="1C Resolver Test",
            connector_type="onec",
            direction="bidirectional",
            enabled=True,
            status="enabled",
            config_json={"mock_odata": {"Catalog_Контрагенты": [{"Ref_Key": "onec-customer", "ИНН": "7701", "Description": "ООО Тест"}]}},
        )
        session.add(connector)
        await session.commit()
        connector_id = str(connector.id)

    odata = await client.post(
        "/api/resolvers",
        json={
            "name": "Resolve Customer OData Test",
            "resolver_code": "test_customer_odata",
            "object_type": "Customer",
            "strategy": "odata",
            "connector_id": connector_id,
            "input_schema_json": {"anyOf": ["inn"]},
            "config_json": {"resource": "Catalog_Контрагенты", "filter_template": "ИНН eq '{{input.inn}}'", "mock_match_fields": ["ИНН"], "mapping": {"uuid": "Ref_Key", "inn": "ИНН", "name": "Description"}},
            "cache_enabled": False,
        },
    )
    assert odata.status_code == 200, odata.text
    resolved_odata = await client.post(f"/api/resolvers/{odata.json()['id']}/resolve", json={"input": {"inn": "7701"}})
    assert resolved_odata.status_code == 200, resolved_odata.text
    assert resolved_odata.json()["object_json"]["uuid"] == "onec-customer"
    assert {artifact["name"] for artifact in resolved_odata.json()["artifacts"]} >= {"resolver_request.json", "resolver_response.json", "resolved_object.json"}

    rest = await client.post(
        "/api/resolvers",
        json={
            "name": "Resolve Product REST Test",
            "resolver_code": "test_product_rest",
            "object_type": "Product",
            "strategy": "rest",
            "input_schema_json": {"anyOf": ["article"]},
            "config_json": {"method": "GET", "path_template": "/products/{{input.article}}", "mock_response_json": {"id": "prod-rest", "article": "SKU-1", "title": "REST Product"}, "mapping": {"uuid": "id", "article": "article", "name": "title"}},
            "cache_enabled": False,
        },
    )
    assert rest.status_code == 200, rest.text
    resolved_rest = await client.post(f"/api/resolvers/{rest.json()['id']}/resolve", json={"input": {"article": "SKU-1"}})
    assert resolved_rest.status_code == 200, resolved_rest.text
    assert resolved_rest.json()["object_json"]["uuid"] == "prod-rest"


async def test_chain_resolver_uses_first_success(client):
    missing = await client.post(
        "/api/resolvers",
        json={"name": "Missing Product Resolver", "resolver_code": "test_product_missing", "object_type": "Product", "strategy": "static_map", "input_schema_json": {"anyOf": ["article"]}, "config_json": {"entries": []}, "cache_enabled": False},
    )
    assert missing.status_code == 200, missing.text
    fallback = await client.post(
        "/api/resolvers",
        json={"name": "Fallback Product Resolver", "resolver_code": "test_product_fallback", "object_type": "Product", "strategy": "static_map", "input_schema_json": {"anyOf": ["article"]}, "config_json": {"entries": [{"match": {"article": "SKU-CHAIN"}, "object": {"uuid": "prod-chain", "article": "SKU-CHAIN"}}]}, "cache_enabled": False},
    )
    assert fallback.status_code == 200, fallback.text
    chain = await client.post(
        "/api/resolvers",
        json={"name": "Chain Product Resolver", "resolver_code": "test_product_chain", "object_type": "Product", "strategy": "chain", "input_schema_json": {"anyOf": ["article"]}, "config_json": {"steps": [{"resolver_code": "test_product_missing", "input": {"article": "input.article"}}, {"resolver_code": "test_product_fallback", "input": {"article": "input.article"}}]}, "cache_enabled": False},
    )
    assert chain.status_code == 200, chain.text
    resolved = await client.post(f"/api/resolvers/{chain.json()['id']}/resolve", json={"input": {"article": "SKU-CHAIN"}})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["success"] is True
    assert resolved.json()["object_json"]["uuid"] == "prod-chain"
    assert resolved.json()["source"]["resolver_code"] == "test_product_fallback"


async def test_resolve_object_execution_step_writes_artifacts(client):
    resolver = await client.post(
        "/api/resolvers",
        json={
            "name": "Execution Customer Resolver",
            "resolver_code": "exec_customer",
            "object_type": "Customer",
            "strategy": "static_map",
            "input_schema_json": {"anyOf": ["inn"]},
            "config_json": {"entries": [{"match": {"inn": "555"}, "object": {"uuid": "cust-exec", "inn": "555", "name": "Execution Customer"}}]},
            "cache_enabled": False,
        },
    )
    assert resolver.status_code == 200, resolver.text
    workflow = await client.post(
        "/api/workflows",
        json={
            "name": "Resolve object workflow",
            "event_type": "ResolveObjectEvent",
            "steps_json": [
                {"name": "receive"},
                {"name": "resolve_customer", "handler": "resolve_object", "config": {"step_id": "resolve_customer", "resolver": "exec_customer", "input": {"inn": "request.body.inn"}, "save_as": "customer", "inject": {"customer_uuid": "customer.uuid"}, "required": True}},
                {"name": "build_payload", "handler": "flow_build_json", "config": {"step_id": "build_payload", "template": {"customer_uuid": "{{customer.uuid}}", "payload_customer_uuid": "{{request.body.customer_uuid}}"}, "save_as": "target_payload"}},
            ],
            "validation_json": {"required_fields": []},
        },
    )
    assert workflow.status_code == 200, workflow.text
    event = await client.post(
        "/api/events",
        json={"source_system": "1C", "target_system": "API", "event_type": "ResolveObjectEvent", "entity_type": "Customer", "entity_id": "555", "payload": {"inn": "555"}},
    )
    assert event.status_code == 200, event.text
    timeline = await client.get(f"/api/events/{event.json()['id']}/timeline")
    assert timeline.status_code == 200, timeline.text
    steps = timeline.json()["runs"][0]["steps"]
    resolve_step = next(step for step in steps if step["step_name"] == "resolve_customer")
    assert resolve_step["status"] == "success"
    artifact_names = {artifact["name"] for artifact in resolve_step["artifacts"]}
    assert {"resolver_input.json", "resolver_cache_result.json", "resolver_request.json", "resolver_response.json", "resolved_object.json"} <= artifact_names
    build_step = next(step for step in steps if step["step_name"] == "build_payload")
    result = next(artifact for artifact in build_step["artifacts"] if artifact["name"] == "json_builder_result.json")
    assert result["content_json"]["customer_uuid"] == "cust-exec"
    assert result["content_json"]["payload_customer_uuid"] == "cust-exec"
