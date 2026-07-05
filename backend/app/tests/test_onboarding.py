async def test_onboarding_state_complete_skip_and_reset(client):
    state = await client.get("/api/onboarding/state")
    assert state.status_code == 200, state.text
    body = state.json()
    assert body["total_count"] >= 8
    assert body["completed_count"] == 0
    assert body["setup_done"] is False
    assert body["items"][0]["key"] == "install_onec_package"

    completed = await client.post("/api/onboarding/complete", json={"key": "install_onec_package", "metadata_json": {"source": "test"}})
    assert completed.status_code == 200, completed.text
    assert completed.json()["completed"] is True
    assert completed.json()["metadata_json"]["source"] == "test"

    skipped = await client.post("/api/onboarding/skip", json={"key": "enable_auth_or_skip"})
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["skipped"] is True

    state = await client.get("/api/onboarding/state")
    assert state.json()["completed_count"] == 2

    reset_one = await client.post("/api/onboarding/reset", json={"key": "install_onec_package"})
    assert reset_one.status_code == 200, reset_one.text
    assert reset_one.json()["completed_count"] == 1

    reset_all = await client.post("/api/onboarding/reset")
    assert reset_all.status_code == 200, reset_all.text
    assert reset_all.json()["completed_count"] == 0


async def test_onboarding_example_runner_creates_timeline(client):
    response = await client.post("/api/onboarding/examples/onec_post_to_api/run")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["timeline_url"].startswith("/events/")

    timeline = await client.get(f"/api/events/{body['event_id']}/timeline")
    assert timeline.status_code == 200, timeline.text
    assert timeline.json()["event"]["event_type"] == "OnboardingOneCPostToApiExample"

    state = await client.get("/api/onboarding/state")
    run_step = next(item for item in state.json()["items"] if item["key"] == "run_first_test_case")
    assert run_step["completed"] is True
    assert run_step["metadata_json"]["example_id"] == "onec_post_to_api"


async def test_onboarding_unknown_example_returns_error(client):
    response = await client.post("/api/onboarding/examples/unknown/run")
    assert response.status_code == 400
    assert "Unknown onboarding example" in response.json()["detail"]
