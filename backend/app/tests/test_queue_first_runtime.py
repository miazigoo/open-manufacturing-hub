async def _workflow(client, name="Queue First Workflow", steps=None, event_type="QueueFirst"):
    response = await client.post(
        "/api/workflows",
        json={"name": name, "event_type": event_type, "steps_json": steps or [{"name": "receive"}, {"name": "handle_response"}], "validation_json": {"required_fields": []}},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_async_bus_persists_queue_item_before_processing(client):
    workflow = await _workflow(client)
    endpoint = await client.post(
        "/api/integration-bus/endpoints",
        json={"name": "Queue first async", "slug": "queue-first-async", "input_mode": "json", "response_mode": "accepted_event", "default_source_system": "1C ERP", "default_target_system": "WMS", "default_event_type": "QueueFirst", "workflow_id": workflow["id"]},
    )
    assert endpoint.status_code == 200, endpoint.text

    accepted = await client.post("/api/bus/in/queue-first-async", json={"order_id": "SO-20"})
    assert accepted.status_code == 200, accepted.text
    body = accepted.json()
    assert body["accepted"] is True
    assert body["queue_item_id"]
    assert body["status"] == "waiting"

    queue_item = (await client.get(f"/api/queue/{body['queue_item_id']}")).json()
    assert queue_item["event_id"] == body["event_id"]
    assert queue_item["status"] == "waiting"
    timeline = (await client.get(f"/api/events/{body['event_id']}/timeline")).json()
    assert timeline["queue_item"]["id"] == body["queue_item_id"]
    assert timeline["runs"] == []


async def test_process_once_completes_waiting_queue_item(client):
    workflow = await _workflow(client, name="Queue Worker Success", event_type="QueueWorkerSuccess")
    endpoint = await client.post("/api/integration-bus/endpoints", json={"name": "Queue worker success", "slug": "queue-worker-success", "input_mode": "json", "response_mode": "accepted_event", "default_event_type": "QueueWorkerSuccess", "workflow_id": workflow["id"]})
    assert endpoint.status_code == 200
    accepted = (await client.post("/api/bus/in/queue-worker-success", json={"id": "ok"})).json()

    processed = await client.post("/api/queue/process-once?worker=test-worker")
    assert processed.status_code == 200, processed.text
    body = processed.json()
    assert body["processed"] == 1
    assert body["completed"] == 1

    queue_item = (await client.get(f"/api/queue/{accepted['queue_item_id']}")).json()
    assert queue_item["status"] == "completed"
    assert queue_item["attempts"] == 1
    timeline = (await client.get(f"/api/events/{accepted['event_id']}/timeline")).json()
    assert timeline["event"]["status"] == "success"


async def test_locked_queue_item_is_not_double_processed(client):
    created = await client.post("/api/queue", json={"business_object": "Order", "operation": "ship", "payload_json": {"id": "locked"}})
    assert created.status_code == 200, created.text
    queue_id = created.json()["id"]
    locked = await client.post(f"/api/enterprise-runtime/queue/{queue_id}/processing?worker=worker-a")
    assert locked.status_code == 200
    assert locked.json()["locked_until"]

    processed = await client.post("/api/queue/process-once?worker=worker-b")
    assert processed.status_code == 200
    assert processed.json()["processed"] == 0


async def test_retry_exhaustion_moves_to_dlq(client):
    created = await client.post("/api/queue", json={"business_object": "Order", "operation": "ship", "max_attempts": 1, "payload_json": {"id": "bad"}})
    assert created.status_code == 200, created.text
    queue_id = created.json()["id"]

    processed = await client.post("/api/queue/process-once?worker=test-worker")
    assert processed.status_code == 200, processed.text
    assert processed.json()["dlq"] == 1
    queue_item = (await client.get(f"/api/queue/{queue_id}")).json()
    assert queue_item["status"] == "dlq"
    dlq = await client.get("/api/dlq")
    assert dlq.status_code == 200
    assert dlq.json()[0]["queue_message_id"] == queue_id
