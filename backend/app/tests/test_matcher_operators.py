import pytest

PAYLOAD = {
    "order": {"number": "260530/6543", "lines": 12},
    "gtin": "04646151697810",
    "serial": "ABC123",
    "tags": ["laser", "dnp"],
}


async def _evaluate(client, rules, mode="all", payload=None):
    response = await client.post(
        "/api/matchers/test",
        json={"input_mode": "json", "payload": payload if payload is not None else PAYLOAD, "matcher_group": {"mode": mode, "rules": rules}},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.anyio
async def test_not_equals_and_not_contains(client):
    result = await _evaluate(client, [
        {"type": "body_path_not_equals", "path": "order.number", "value": "000000/0000"},
        {"type": "body_path_not_contains", "path": "serial", "value": "ZZZ"},
    ])
    assert result["matched"] is True

    result = await _evaluate(client, [{"type": "body_path_not_equals", "path": "order.number", "value": "260530/6543"}])
    assert result["matched"] is False
    assert result["trace"][0]["actual"] == "260530/6543"


@pytest.mark.anyio
async def test_in_and_not_in(client):
    result = await _evaluate(client, [{"type": "body_path_in", "path": "gtin", "values": ["04646151697810", "111"]}])
    assert result["matched"] is True
    result = await _evaluate(client, [{"type": "body_path_not_in", "path": "gtin", "values": ["111", "222"]}])
    assert result["matched"] is True
    result = await _evaluate(client, [{"type": "body_path_not_in", "path": "gtin", "values": ["04646151697810"]}])
    assert result["matched"] is False


@pytest.mark.anyio
async def test_starts_with_ends_with(client):
    result = await _evaluate(client, [
        {"type": "body_path_starts_with", "path": "gtin", "value": "0464"},
        {"type": "body_path_ends_with", "path": "serial", "value": "123"},
    ])
    assert result["matched"] is True
    result = await _evaluate(client, [{"type": "body_path_starts_with", "path": "gtin", "value": "9999"}])
    assert result["matched"] is False


@pytest.mark.anyio
async def test_numeric_comparisons(client):
    result = await _evaluate(client, [
        {"type": "body_path_gt", "path": "order.lines", "value": 10},
        {"type": "body_path_le", "path": "order.lines", "value": 12},
        {"type": "body_path_ge", "path": "order.lines", "value": 12},
        {"type": "body_path_lt", "path": "order.lines", "value": 20},
    ])
    assert result["matched"] is True
    result = await _evaluate(client, [{"type": "body_path_gt", "path": "order.lines", "value": 12}])
    assert result["matched"] is False


@pytest.mark.anyio
async def test_numeric_comparison_with_non_numeric_value_does_not_match(client):
    result = await _evaluate(client, [{"type": "body_path_gt", "path": "serial", "value": 5}])
    assert result["matched"] is False
    assert "numbers" in (result["trace"][0]["message"] or "")


@pytest.mark.anyio
async def test_body_path_regex(client):
    result = await _evaluate(client, [{"type": "body_path_regex", "path": "order.number", "pattern": r"^\d{6}/\d{4}$"}])
    assert result["matched"] is True
    result = await _evaluate(client, [{"type": "body_path_regex", "path": "gtin", "pattern": r"[A-Z]"}])
    assert result["matched"] is False


@pytest.mark.anyio
async def test_nested_groups(client):
    # gtin starts with 9999 OR (serial ends with 123 AND lines >= 10)
    result = await _evaluate(client, [
        {"type": "body_path_starts_with", "path": "gtin", "value": "9999"},
        {"group": {"mode": "all", "rules": [
            {"type": "body_path_ends_with", "path": "serial", "value": "123"},
            {"type": "body_path_ge", "path": "order.lines", "value": 10},
        ]}},
    ], mode="any")
    assert result["matched"] is True
    group_trace = result["trace"][1]
    assert group_trace["rule"] == "group"
    assert group_trace["matched"] is True
    assert len(group_trace["trace"]) == 2


@pytest.mark.anyio
async def test_nested_group_depth_is_limited(client):
    leaf = {"mode": "all", "rules": [{"type": "always"}]}
    too_deep = {"mode": "all", "rules": [{"group": {"mode": "all", "rules": [{"group": {"mode": "all", "rules": [{"group": leaf}]}}]}}]}
    response = await client.post(
        "/api/matchers/test",
        json={"input_mode": "json", "payload": PAYLOAD, "matcher_group": too_deep},
    )
    assert response.status_code == 400, response.text
    assert "nested" in response.text


@pytest.mark.anyio
async def test_invalid_regex_reports_message_instead_of_crashing(client):
    result = await _evaluate(client, [{"type": "body_path_regex", "path": "gtin", "pattern": "([unclosed"}])
    assert result["matched"] is False
    assert result["trace"][0]["message"]
