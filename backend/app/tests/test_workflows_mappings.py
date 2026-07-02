from app.core.enums import RunStatus


def _source_mapping_payload():
    return {
        "name": "ERP SalesOrder to Canonical",
        "source_entity": "SalesOrder",
        "target_entity": "SalesOrder",
        "initial_version": {
            "rules_json": [
                {"source": "order_id", "target": "id", "transform": "str"},
                {"source": "warehouse_id", "target": "warehouse.id", "transform": "str"},
                {
                    "source": "items",
                    "target": "lines",
                    "type": "array",
                    "items": [
                        {"source": "sku", "target": "sku"},
                        {"source": "qty", "target": "quantity"},
                    ],
                },
                {"constant": "SalesOrder", "target": "entity"},
            ],
            "source_schema_json": {"order_id": "string", "warehouse_id": "string", "items": []},
            "target_schema_json": {"id": "string", "warehouse": {"id": "string"}, "lines": []},
        },
    }


def _target_mapping_payload():
    return {
        "name": "Canonical SalesOrder to WMS",
        "source_entity": "SalesOrder",
        "target_entity": "Shipment",
        "initial_version": {
            "rules_json": [
                {"source": "id", "target": "target_order_id"},
                {"source": "warehouse.id", "target": "warehouse_id"},
                {
                    "source": "lines",
                    "target": "lines",
                    "type": "array",
                    "items": [
                        {"source": "sku", "target": "sku"},
                        {"source": "quantity", "target": "qty"},
                    ],
                },
                {"expression": "concat('SO-', $.id)", "target": "external_ref"},
            ],
            "source_schema_json": {"id": "string", "warehouse": {"id": "string"}, "lines": []},
            "target_schema_json": {"target_order_id": "string", "warehouse_id": "string", "lines": []},
        },
    }


async def test_mapping_execution_versioning_diff_and_validation(client):
    create_response = await client.post("/api/mappings", json=_source_mapping_payload())
    assert create_response.status_code == 200
    mapping = create_response.json()
    assert len(mapping["versions"]) == 1

    execute_response = await client.post(
        f"/api/mappings/{mapping['id']}/versions/1/execute",
        json={"payload": {"order_id": 1532, "warehouse_id": 5, "items": [{"sku": "A", "qty": 2}]}},
    )
    assert execute_response.status_code == 200
    assert execute_response.json()["output"]["warehouse"]["id"] == "5"

    clone_response = await client.post(f"/api/mappings/{mapping['id']}/versions/1/clone", json={"notes": "v2 baseline"})
    assert clone_response.status_code == 200
    assert clone_response.json()["version"] == 2

    version_response = await client.post(
        f"/api/mappings/{mapping['id']}/versions",
        json={"rules_json": [{"source": "order_id", "target": "id"}, {"constant": True, "target": "active"}]},
    )
    assert version_response.status_code == 200
    assert version_response.json()["version"] == 3

    diff_response = await client.get(f"/api/mappings/{mapping['id']}/compare?left_version=1&right_version=3")
    assert diff_response.status_code == 200
    diff = diff_response.json()
    assert any(rule["target"] == "active" for rule in diff["added"])
    assert diff["changed"]

    invalid_response = await client.post("/api/mappings/validate", json={"rules_json": [{"source": "id"}]})
    assert invalid_response.status_code == 200
    assert invalid_response.json()["valid"] is False


async def test_workflow_selection_runs_mapping_versions_and_dry_run(client, success_payload):
    source_mapping = (await client.post("/api/mappings", json=_source_mapping_payload())).json()
    target_mapping = (await client.post("/api/mappings", json=_target_mapping_payload())).json()
    source_version_id = source_mapping["versions"][0]["id"]
    target_version_id = target_mapping["versions"][0]["id"]

    workflow_response = await client.post(
        "/api/workflows",
        json={
            "name": "Sales orders ERP to WMS",
            "event_type": "SalesOrderCreated",
            "source_system": "Mock ERP",
            "target_system": "Mock WMS",
            "entity_type": "SalesOrder",
            "source_mapping_version_id": source_version_id,
            "target_mapping_version_id": target_version_id,
        },
    )
    assert workflow_response.status_code == 200
    workflow = workflow_response.json()

    response = await client.post("/api/events", json=success_payload)
    assert response.status_code == 200
    event = response.json()

    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    run = timeline["runs"][0]
    assert run["workflow_name"] == "Sales orders ERP to WMS"
    assert run["mapping_versions_json"]["source"]["version"] == 1
    assert run["mapping_versions_json"]["target"]["version"] == 1
    map_step = next(step for step in run["steps"] if step["step_name"] == "map_to_target")
    mapped_artifact = next(artifact for artifact in map_step["artifacts"] if artifact["artifact_type"] == "mapped_payload")
    assert mapped_artifact["content_json"]["external_ref"] == "SO-1532"

    dry_run_response = await client.post(
        f"/api/workflows/{workflow['id']}/dry-run",
        json={"payload": success_payload["payload"], "source_system": "Mock ERP", "target_system": "Mock WMS", "entity_type": "SalesOrder"},
    )
    assert dry_run_response.status_code == 200
    assert dry_run_response.json()["status"] == RunStatus.DRY_RUN_SUCCESS


async def test_workflow_can_be_disabled(client):
    response = await client.post(
        "/api/workflows",
        json={"name": "Disabled route", "event_type": "Noop", "enabled": True},
    )
    workflow = response.json()
    disable_response = await client.post(f"/api/workflows/{workflow['id']}/disable")
    assert disable_response.status_code == 200
    assert disable_response.json()["enabled"] is False
