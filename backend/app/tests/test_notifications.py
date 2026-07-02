from app.notifications import channels


async def test_incident_created_rule_creates_webhook_delivery_log(client, failed_payload, monkeypatch):
    async def fake_webhook(url, payload):
        return True, {"status_code": 202}, None

    monkeypatch.setattr(channels, "send_webhook", fake_webhook)
    await client.post(
        "/api/notifications/rules",
        json={
            "name": "Critical WMS errors",
            "trigger_type": "incident_created",
            "filters": {"target_system": "Mock WMS", "severity": "error"},
            "channels": [{"type": "webhook", "url": "https://example.com/integration-alert"}],
            "cooldown_seconds": 600,
        },
    )

    await client.post("/api/events", json=failed_payload)
    deliveries = (await client.get("/api/notifications/deliveries")).json()
    assert len(deliveries) == 1
    assert deliveries[0]["target_channel"] == "webhook"
    assert deliveries[0]["status"] == "sent"


async def test_cooldown_prevents_repeated_send(client, failed_payload, monkeypatch):
    async def fake_webhook(url, payload):
        return True, {"status_code": 202}, None

    monkeypatch.setattr(channels, "send_webhook", fake_webhook)
    await client.post(
        "/api/notifications/rules",
        json={
            "name": "Incident updates",
            "trigger_type": "incident_updated",
            "channels": [{"type": "webhook", "url": "https://example.com/integration-alert"}],
            "cooldown_seconds": 600,
        },
    )

    await client.post("/api/events", json=failed_payload)
    payload2 = dict(failed_payload)
    payload2["entity_id"] = "1533"
    payload2["payload"] = dict(failed_payload["payload"], order_id="1533")
    await client.post("/api/events", json=payload2)
    payload3 = dict(failed_payload)
    payload3["entity_id"] = "1534"
    payload3["payload"] = dict(failed_payload["payload"], order_id="1534")
    await client.post("/api/events", json=payload3)

    statuses = [delivery["status"] for delivery in (await client.get("/api/notifications/deliveries")).json()]
    assert statuses.count("sent") == 1
    assert statuses.count("skipped_cooldown") == 1


async def test_test_notification_and_email_stub_create_delivery_log(client):
    rule = (await client.post(
        "/api/notifications/rules",
        json={
            "name": "Email stub",
            "trigger_type": "incident_created",
            "channels": [{"type": "email_stub", "to": "dev@example.com"}],
        },
    )).json()

    response = await client.post(f"/api/notifications/rules/{rule['id']}/test")
    assert response.status_code == 200
    delivery = response.json()[0]
    assert delivery["target_channel"] == "email_stub"
    assert delivery["status"] == "sent"
