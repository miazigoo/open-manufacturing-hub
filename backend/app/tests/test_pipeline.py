from app.pipeline.steps import map_to_target, normalize, validate


def test_mock_pipeline_steps_are_deterministic():
    payload = {"order_id": "1532", "warehouse_id": 5, "items": []}
    normalized = normalize(payload)
    assert normalized["warehouse_id"] == "5"
    assert validate(normalized) == {"valid": True, "missing": []}
    assert map_to_target(normalized)["target_order_id"] == "1532"
