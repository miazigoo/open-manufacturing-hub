async def test_agent_heartbeat_creates_health_info_and_dashboard_site(client):
    response = await client.post(
        "/api/health/agent-heartbeat",
        json={
            "site_name": "Main Warehouse",
            "site_code": "main",
            "agent_name": "agent-1",
            "internet_ok": False,
            "can_reach_hub": True,
            "can_reach_wms": False,
            "can_reach_erp": True,
        },
    )
    assert response.status_code == 200

    dashboard = (await client.get("/api/health/dashboard")).json()
    site = dashboard["sites"][0]
    assert site["name"] == "Main Warehouse"
    assert site["status"] == "down"
    assert site["internet"] == "down"
    assert site["wms"] == "down"
    assert site["erp"] == "ok"


async def test_connector_status_appears_in_dashboard(client):
    response = await client.post(
        "/api/health/checks",
        json={"component_type": "connector", "component_name": "Mock WMS", "status": "warning"},
    )
    assert response.status_code == 200

    dashboard = (await client.get("/api/health/dashboard")).json()
    assert {component["name"]: component["status"] for component in dashboard["components"]}["Mock WMS"] == "warning"
