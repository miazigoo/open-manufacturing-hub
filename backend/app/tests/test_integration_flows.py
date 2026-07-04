async def test_matcher_api_and_integration_flow_marking_pool(client):
    matcher = await client.post(
        "/api/matchers/test",
        json={
            "input_mode": "json",
            "payload": {"pool": {"type": "DNP"}, "codes": ["a"]},
            "matcher_group": {"mode": "all", "rules": [{"type": "body_path_equals", "path": "pool.type", "value": "DNP"}, {"type": "body_path_exists", "path": "codes"}]},
        },
    )
    assert matcher.status_code == 200, matcher.text
    assert matcher.json()["matched"] is True
    assert matcher.json()["trace"][0]["actual"] == "DNP"

    installed = await client.post("/api/scenario-library/marking-pool-to-internal-service/install")
    assert installed.status_code == 200, installed.text
    flow = installed.json()
    assert flow["slug"] == "marking-pool"
    assert flow["endpoint_url"] == "/api/bus/in/marking-pool"
    assert "HTTPСоединение" in flow["onec_http_example"]

    scenarios = await client.get("/api/scenario-library")
    assert scenarios.status_code == 200
    assert "marking_pool_to_internal_service" in {item["code"] for item in scenarios.json()}

    generic_install = await client.post("/api/scenario-library/marking_pool_to_internal_service/install")
    assert generic_install.status_code == 200, generic_install.text
    assert generic_install.json()["test_case_id"]

    flows = await client.get("/api/integration-flows")
    assert flows.status_code == 200
    assert any(item["slug"] == "marking-pool" for item in flows.json())

    dry_run = await client.post(
        f"/api/integration-flows/{flow['id']}/test",
        json={"input_mode": "json", "payload_json": {"pool_type": "DNP", "codes": ["010"], "order_id": "ORD-1"}, "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["matcher"]["matched"] is True
    assert dry_run.json()["bus_response"] is None

    sent = await client.post("/api/bus/in/marking-pool", json={"pool_type": "DNP", "codes": ["010"], "order_id": "ORD-1"})
    assert sent.status_code == 200, sent.text
    body = sent.json()
    assert body["event_id"]
    assert body["route_id"] == flow["route_id"]

    timeline = await client.get(f"/api/events/{body['event_id']}/timeline")
    assert timeline.status_code == 200
    artifacts = timeline.json()["runs"][0]["steps"][0]["artifacts"]
    trace_artifact = next(item for item in artifacts if item["name"] == "route_match_trace.json")
    assert trace_artifact["content_json"]["selected_route"] == "Flow 1C Marking Code Pool to Internal Service Route"

    exported = await client.get(f"/api/integration-flows/{flow['id']}/export")
    assert exported.status_code == 200
    assert exported.json()["config"]["matcher_group"]["rules"][0]["type"] == "body_path_equals"
