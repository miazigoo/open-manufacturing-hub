async def test_ui_cockpit_summary_and_options(client):
    installed = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": True})
    assert installed.status_code == 200, installed.text

    summary = await client.get("/api/ui/cockpit/summary")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["package_state"]["package_id"] == "omh-package-onec"
    assert body["package_state"]["enabled"] is True
    assert any(action["code"] == "onec_post_two_odata_to_endpoint" for action in body["quick_actions"])
    assert "enabled_integrations" in body["metrics"]

    options = await client.get("/api/ui/cockpit/options")
    assert options.status_code == 200, options.text
    options_body = options.json()
    assert "json" in options_body["input_modes"]
    assert "proxy_response" in options_body["response_modes"]
    assert isinstance(options_body["onec_connectors"], list)


async def test_ui_flow_builder_options_and_state(client):
    installed = await client.post("/api/scenario-library/onec-post-two-odata-to-endpoint/install")
    assert installed.status_code == 200, installed.text
    flow = installed.json()

    options = await client.get("/api/ui/flow-builder/options")
    assert options.status_code == 200, options.text
    body = options.json()
    assert "body_path_equals" in body["matcher_types"]
    assert any(step["type"] == "odata_query" for step in body["available_steps"])

    state = await client.get(f"/api/ui/flow-builder/{flow['id']}/state")
    assert state.status_code == 200, state.text
    assert state.json()["flow_id"] == flow["id"]
    assert state.json()["builder_json"]["steps"][2]["type"] == "odata_query"


async def test_ui_package_disabled_reflected_in_navigation_and_options(client):
    await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    disabled = await client.post("/api/packages/omh-package-onec/disable")
    assert disabled.status_code == 200, disabled.text

    summary = await client.get("/api/ui/cockpit/summary")
    assert summary.status_code == 200
    assert summary.json()["package_state"]["enabled"] is False

    navigation = await client.get("/api/ui/navigation")
    assert navigation.status_code == 200
    cockpit = next(item for item in navigation.json() if item["route"] == "/onec-cockpit")
    assert cockpit["enabled"] is False
