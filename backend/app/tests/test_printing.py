async def _create_printer(client):
    connector_response = await client.post(
        "/api/connectors",
        json={
            "name": "Line 1 Zebra",
            "connector_type": "zpl_printer",
            "direction": "target",
            "config_json": {"printer_name": "Line 1 Zebra", "host": "zebra-line-1.local", "port": 9100, "dpi": 203, "timeout_seconds": 5},
        },
    )
    assert connector_response.status_code == 200
    printer_response = await client.post(
        "/api/printing/printers",
        json={"name": "Line 1", "connector_id": connector_response.json()["id"], "dpi": 203},
    )
    assert printer_response.status_code == 200
    return printer_response.json()


async def test_printing_job_lifecycle(client):
    printer = await _create_printer(client)
    job_response = await client.post(
        "/api/printing/jobs",
        json={
            "job_key": "print-job-1001",
            "printer_id": printer["id"],
            "source_system": "1C WMS",
            "source_document_id": "DOC-1001",
            "source_document_name": "Маркировка 1001",
            "lines": [
                {"sequence_no": 1, "code": "010460123456789021ABC", "zpl": "^XA\n^FO0,0\n^FDABC^FS\n^XZ"},
                {"sequence_no": 2, "code": "010460123456789021DEF", "zpl": "^XA\n^FO0,0\n^FDDEF^FS\n^XZ"},
            ],
        },
    )
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["status"] == "ready"
    assert job["total_lines"] == 2

    batch_response = await client.post(f"/api/printing/jobs/{job['id']}/send-batch", json={"limit": 1, "dry_run": True})
    assert batch_response.status_code == 200
    batch = batch_response.json()
    assert batch["processed"] == 1
    assert batch["sent"] == 1
    assert batch["job"]["status"] == "partially_sent"

    lines = (await client.get(f"/api/printing/jobs/{job['id']}/lines")).json()
    assert lines[0]["status"] == "test_mode"
    assert lines[0]["attempts"] == 1

    confirm_response = await client.post(f"/api/printing/jobs/{job['id']}/confirm-printed", json={"through_sequence_no": 1})
    assert confirm_response.status_code == 200
    assert confirm_response.json()["printed_lines"] == 1

    return_response = await client.post(f"/api/printing/jobs/{job['id']}/return-to-print", json={"from_sequence_no": 1, "reason": "Label damaged"})
    assert return_response.status_code == 200

    logs = (await client.get(f"/api/printing/jobs/{job['id']}/logs")).json()
    actions = {log["action"] for log in logs}
    assert {"job_created", "batch_started", "line_reserved", "line_sent", "line_confirmed_printed", "line_returned_to_print"}.issubset(actions)


async def test_printing_job_key_is_idempotent_but_rejects_different_payload(client):
    printer = await _create_printer(client)
    payload = {
        "job_key": "print-job-idempotent",
        "printer_id": printer["id"],
        "source_system": "1C ERP",
        "lines": [
            {"sequence_no": 1, "code": "010460123456789021ABC", "zpl": "^XA\n^FO0,0\n^FDABC^FS\n^XZ"},
        ],
    }

    first = await client.post("/api/printing/jobs", json=payload)
    assert first.status_code == 200
    second = await client.post("/api/printing/jobs", json=payload)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    changed = dict(payload)
    changed["lines"] = [{"sequence_no": 1, "code": "010460123456789021CHANGED", "zpl": "^XA\n^FO0,0\n^FDABC^FS\n^XZ"}]
    rejected = await client.post("/api/printing/jobs", json=changed)
    assert rejected.status_code == 400
    assert "already exists with different lines" in rejected.json()["detail"]
