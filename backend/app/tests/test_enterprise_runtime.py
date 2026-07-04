async def test_enterprise_runtime_queue_dlq_monitor_resolvers_transforms_rules(client):
    presets = await client.post("/api/enterprise-runtime/install-presets")
    assert presets.status_code == 200, presets.text
    assert presets.json()["canonical_objects"] >= 12

    objects = await client.get("/api/enterprise-runtime/canonical-objects")
    assert objects.status_code == 200
    assert {item["name"] for item in objects.json()} >= {"Customer", "SalesOrder", "PrintJob"}

    queue = await client.post(
        "/api/enterprise-runtime/queue",
        json={"business_object": "SalesOrder", "operation": "ship", "priority": 10, "payload_json": {"order_id": "SO-1001"}},
    )
    assert queue.status_code == 200, queue.text
    queue_id = queue.json()["id"]

    processing = await client.post(f"/api/enterprise-runtime/queue/{queue_id}/processing?worker=test-worker")
    assert processing.status_code == 200
    assert processing.json()["status"] == "processing"
    assert processing.json()["attempts"] == 1

    dlq = await client.post(f"/api/enterprise-runtime/queue/{queue_id}/dlq?reason=boom")
    assert dlq.status_code == 200, dlq.text
    assert dlq.json()["reason"] == "boom"

    monitor = await client.get("/api/enterprise-runtime/monitor")
    assert monitor.status_code == 200
    assert monitor.json()["dlq"] == 1

    retry = await client.post(f"/api/enterprise-runtime/dlq/{dlq.json()['id']}/retry")
    assert retry.status_code == 200
    assert retry.json()["status"] == "waiting"

    archive = await client.post(f"/api/enterprise-runtime/dlq/{dlq.json()['id']}/archive")
    assert archive.status_code == 200
    assert archive.json()["archived"] is True

    resolvers = await client.get("/api/enterprise-runtime/resolvers")
    assert resolvers.status_code == 200
    warehouse = next(item for item in resolvers.json() if item["name"] == "ResolveWarehouse")

    preload = await client.post(
        "/api/enterprise-runtime/odata-cache/preload",
        json={"resolver_name": "ResolveWarehouse", "lookup_key": "MAIN", "value_json": {"uuid": "wh-main"}},
    )
    assert preload.status_code == 200

    resolved = await client.post(f"/api/enterprise-runtime/resolvers/{warehouse['id']}/resolve", json={"input": {"warehouse_id": "MAIN"}})
    assert resolved.status_code == 200
    assert resolved.json()["cache_status"] == "hit"
    assert resolved.json()["value"]["uuid"] == "wh-main"

    transformed = await client.post("/api/enterprise-runtime/transforms/apply", json={"name": "uppercase", "value": "omh"})
    assert transformed.status_code == 200
    assert transformed.json()["result"] == "OMH"

    rules = await client.get("/api/enterprise-runtime/business-rules")
    assert rules.status_code == 200
    rule = next(item for item in rules.json() if item["name"] == "Stop cancelled orders")
    rule_run = await client.post(f"/api/enterprise-runtime/business-rules/{rule['id']}/run", json={"payload": {"status": "cancelled"}})
    assert rule_run.status_code == 200
    assert rule_run.json()["failed"] == "Cancelled order cannot be shipped"
