from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import update

from app.core.database import async_session
from app.health.models import AgentHeartbeat


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
    assert site["code"] == "main"
    assert site["status"] == "down"
    assert site["internet"] == "down"
    assert site["hub"] == "ok"
    assert site["wms"] == "down"
    assert site["erp"] == "ok"
    assert site["agent_name"] == "agent-1"
    assert site["agent_status"] == "warning"
    assert site["heartbeat_age_seconds"] is not None

    agents = (await client.get("/api/health/agents")).json()
    assert len(agents) == 1
    assert agents[0]["site_code"] == "main"
    assert agents[0]["agent_name"] == "agent-1"
    assert agents[0]["status"] == "warning"
    assert agents[0]["hub"] == "ok"


async def test_agent_heartbeat_history_supports_site_filter(client):
    for site_code in ["main", "remote"]:
        response = await client.post(
            "/api/health/agent-heartbeat",
            json={
                "site_name": f"{site_code.title()} Warehouse",
                "site_code": site_code,
                "agent_name": "edge-agent",
                "internet_ok": True,
                "can_reach_hub": True,
                "can_reach_wms": True,
                "local_ip": "10.0.0.10",
                "details_json": {"version": "0.1.0"},
            },
        )
        assert response.status_code == 200

    history = (await client.get("/api/health/agent-heartbeats", params={"site_code": "remote"})).json()
    assert len(history) == 1
    assert history[0]["site_code"] == "remote"
    assert history[0]["local_ip"] == "10.0.0.10"
    assert history[0]["details_json"]["version"] == "0.1.0"


async def test_agent_heartbeat_reuses_existing_site_by_name_when_code_differs(client):
    first = await client.post(
        "/api/health/agent-heartbeat",
        json={
            "site_name": "Main Warehouse",
            "site_code": "MAIN",
            "agent_name": "agent-upper",
            "internet_ok": True,
            "can_reach_hub": True,
        },
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/health/agent-heartbeat",
        json={
            "site_name": "Main Warehouse",
            "site_code": "main",
            "agent_name": "agent-lower",
            "internet_ok": True,
            "can_reach_hub": True,
        },
    )
    assert second.status_code == 200
    assert second.json()["site_id"] == first.json()["site_id"]


async def test_stale_agent_summary_is_down(client):
    response = await client.post(
        "/api/health/agent-heartbeat",
        json={
            "site_name": "Cold Warehouse",
            "site_code": "cold",
            "agent_name": "agent-cold",
            "internet_ok": True,
            "can_reach_hub": True,
            "can_reach_wms": True,
        },
    )
    assert response.status_code == 200
    heartbeat_id = UUID(response.json()["id"])

    async with async_session() as session:
        await session.execute(
            update(AgentHeartbeat)
            .where(AgentHeartbeat.id == heartbeat_id)
            .values(received_at=datetime.now(timezone.utc) - timedelta(minutes=10))
        )
        await session.commit()

    agents = (await client.get("/api/health/agents")).json()
    cold = next(agent for agent in agents if agent["site_code"] == "cold")
    assert cold["status"] == "down"
    assert cold["heartbeat_age_seconds"] >= 500


async def test_connector_status_appears_in_dashboard(client):
    response = await client.post(
        "/api/health/checks",
        json={"component_type": "connector", "component_name": "Mock WMS", "status": "warning"},
    )
    assert response.status_code == 200

    dashboard = (await client.get("/api/health/dashboard")).json()
    assert {component["name"]: component["status"] for component in dashboard["components"]}["Mock WMS"] == "warning"


async def test_live_and_ready_health_endpoints(client):
    live = await client.get("/api/health/live")
    assert live.status_code == 200, live.text
    assert live.json()["status"] == "ok"
    assert live.json()["version"]

    ready = await client.get("/api/health/ready")
    assert ready.status_code == 200, ready.text
    body = ready.json()
    assert body["status"] in {"ok", "warning"}
    checks = {item["name"]: item for item in body["checks"]}
    assert checks["database"]["status"] == "ok"
    assert "package_registry" in checks
