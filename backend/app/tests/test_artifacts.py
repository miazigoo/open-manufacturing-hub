async def test_diff_detects_warehouse_id_change(client, failed_payload):
    event = (await client.post("/api/events", json=failed_payload)).json()
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    raw_artifact = timeline["runs"][0]["steps"][0]["artifacts"][0]

    edited = dict(raw_artifact["content_json"])
    edited["warehouse_id"] = "MAIN"
    await client.post(
        f"/api/artifacts/{raw_artifact['id']}/edit-replay",
        json={"edited_content": edited, "start_from_step": "validate"},
    )
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    edited_artifact = next(a for a in timeline["runs"][-1]["artifacts"] if a["name"].startswith("edited_"))

    response = await client.get(f"/api/artifacts/{raw_artifact['id']}/diff", params={"compare_with": edited_artifact["id"]})
    assert response.status_code == 200
    diff = response.json()
    assert diff["changed"]["warehouse_id"] == {"from": "005", "to": "MAIN"}
