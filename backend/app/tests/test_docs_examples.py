async def test_docs_examples_list_get_and_safe_run(client):
    list_response = await client.get("/api/docs/examples")
    assert list_response.status_code == 200, list_response.text
    examples = list_response.json()
    ids = {item["id"] for item in examples}
    assert "onec.two_odata_to_json_endpoint" in ids
    assert "onec.print_label" in ids
    assert "training.onec.post_two_odata_to_dnp" in ids

    get_response = await client.get("/api/docs/examples/onec.two_odata_to_json_endpoint")
    assert get_response.status_code == 200, get_response.text
    example = get_response.json()
    assert example["endpoint_slug"] == "onec-enrich-order"
    assert example["input_mode"] == "json"
    assert example["body"]["inn"] == "7707083893"

    run_response = await client.post("/api/docs/examples/onec.two_odata_to_json_endpoint/run")
    assert run_response.status_code == 200, run_response.text
    result = run_response.json()
    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["requires_setup"] is True
    assert result["response"]["status"] == "requires_setup"
    assert result["response"]["open_in_test_console"] == "/test-console?exampleId=onec.two_odata_to_json_endpoint"


async def test_docs_example_missing_returns_404(client):
    response = await client.get("/api/docs/examples/missing.example")
    assert response.status_code == 404

    run_response = await client.post("/api/docs/examples/missing.example/run")
    assert run_response.status_code == 404
