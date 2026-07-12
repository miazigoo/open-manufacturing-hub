async def test_training_package_install_status_mocks_and_examples(client):
    available = await client.get("/api/packages/available")
    assert available.status_code == 200, available.text
    training_available = next(item for item in available.json() if item["manifest"]["package_id"] == "omh-package-training")
    assert training_available["available"] is True
    assert "training_sandbox" in training_available["manifest"]["capabilities"]

    status_before = await client.get("/api/training/status")
    assert status_before.status_code == 200, status_before.text
    assert status_before.json()["sandbox_installed"] is False

    install = await client.post("/api/training/install")
    assert install.status_code == 200, install.text
    body = install.json()
    assert body["package_id"] == "omh-package-training"
    assert {item["name"] for item in body["connectors"]} >= {"Training OData ERP", "Training OData WMS", "Training DNP API", "Training External API", "Training Printer"}
    assert {item["slug"] for item in body["flows"]} >= {
        "training-onec-two-odata-dnp",
        "training-error-dnp-rejected",
        "training-onec-printer",
        "training-onec-lookup-order-products-xml",
        "training-onec-xml-lookup-order-response",
        "training-print-labels",
        "training-wms-shipment-fact-to-onec",
    }
    assert {item["id"] for item in body["examples"]} >= {
        "training.onec.post_two_odata_to_dnp",
        "training.onec.lookup_order_products_xml",
        "training.onec.xml_lookup_order_response",
        "training.polling.odata_orders_to_wms",
        "training.print.labels",
        "training.wms.shipment_fact_to_onec",
        "training.errors.printer_offline",
    }
    assert {item["slug"] for item in body["polling_jobs"]} == {"training-poll-odata-orders-to-wms"}

    status_after = await client.get("/api/training/status")
    assert status_after.status_code == 200, status_after.text
    assert status_after.json()["sandbox_installed"] is True
    assert len(status_after.json()["test_cases"]) == 13
    assert status_after.json()["polling_jobs"][0]["schedule_type"] == "manual_only"

    resources = await client.get(
        "/api/training/mock-odata/erp/odata/standard.odata/Catalog_Контрагенты",
        params={"$filter": "ИНН eq '7707083893' and DeletionMark eq false", "$select": "Ref_Key,Description,ИНН", "$top": 1},
    )
    assert resources.status_code == 200, resources.text
    assert resources.json()["value"] == [{"Ref_Key": "11111111-1111-1111-1111-111111111111", "Description": "ООО Ромашка", "ИНН": "7707083893"}]

    contains = await client.get(
        "/api/training/mock-odata/erp/odata/standard.odata/Catalog_Номенклатура",
        params={"$filter": "contains(Description,'Сок')", "$select": "Description,Артикул", "$top": 5},
    )
    assert contains.status_code == 200, contains.text
    assert contains.json()["value"][0]["Артикул"] == "A-100"

    dnp_ok = await client.post(
        "/api/training/mock-dnp/marking/pools",
        json={
            "pool_id": "POOL-001",
            "order_id": "SO-1001",
            "inn": "7707083893",
            "product_code": "A-100",
            "codes": ["010464615169738421ABC"],
        },
    )
    assert dnp_ok.status_code == 200, dnp_ok.text
    assert dnp_ok.json()["success"] is True
    assert dnp_ok.json()["accepted_codes"] == 1
    dnp_validation = await client.post("/api/training/mock-dnp/marking/pools", json={"pool_id": "POOL-001"})
    assert dnp_validation.status_code == 422
    assert dnp_validation.json()["error"] == "DNP_CONTRACT_VALIDATION_FAILED"
    assert dnp_validation.json()["field_errors"]["codes"] == "non_empty_array_required"
    dnp_error = await client.post("/api/training/mock-dnp/marking/pools", json={"pool_id": "POOL-ERROR"})
    assert dnp_error.status_code == 400
    assert dnp_error.json()["error"] == "DNP_POOL_REJECTED"

    printer_ok = await client.post("/api/training/mock-printer/print", json={"printer": "TRAINING-PRINTER-01"})
    assert printer_ok.status_code == 200
    assert printer_ok.json()["status"] == "sent"
    printer_error = await client.post("/api/training/mock-printer/print", json={"printer": "TRAINING-OFFLINE"})
    assert printer_error.status_code == 503
    assert printer_error.json()["error"] == "TRAINING_PRINTER_OFFLINE"

    example = await client.get("/api/training/examples/training.onec.post_two_odata_to_dnp")
    assert example.status_code == 200, example.text
    assert example.json()["endpoint_slug"] == "training-onec-two-odata-dnp"

    run = await client.post("/api/training/examples/training.onec.post_two_odata_to_dnp/run")
    assert run.status_code == 200, run.text
    run_body = run.json()
    assert run_body["requires_setup"] is False
    assert run_body["success"] is True
    assert run_body["timeline_url"].startswith("/events/")

    xml_example = await client.get("/api/training/examples/training.onec.lookup_order_products_xml")
    assert xml_example.status_code == 200, xml_example.text
    assert xml_example.json()["endpoint_slug"] == "training-onec-lookup-order-products-xml"

    xml_run = await client.post("/api/training/examples/training.onec.lookup_order_products_xml/run")
    assert xml_run.status_code == 200, xml_run.text
    assert xml_run.json()["requires_setup"] is False
    assert xml_run.json()["success"] is True

    print_labels_example = await client.get("/api/training/examples/training.print.labels")
    assert print_labels_example.status_code == 200, print_labels_example.text
    assert print_labels_example.json()["endpoint_slug"] == "training-print-labels"

    print_labels_run = await client.post("/api/training/examples/training.print.labels/run")
    assert print_labels_run.status_code == 200, print_labels_run.text
    assert print_labels_run.json()["requires_setup"] is False
    assert print_labels_run.json()["success"] is True

    polling_example = await client.get("/api/training/examples/training.polling.odata_orders_to_wms")
    assert polling_example.status_code == 200, polling_example.text
    assert polling_example.json()["endpoint_slug"] == "training-poll-odata-orders-to-wms"

    polling_run = await client.post("/api/training/examples/training.polling.odata_orders_to_wms/run")
    assert polling_run.status_code == 200, polling_run.text
    polling_body = polling_run.json()
    assert polling_body["requires_setup"] is False
    assert polling_body["success"] is True
    assert polling_body["timeline_url"].startswith("/polling?jobId=")
    assert polling_body["response"]["sent_count"] == 2
    assert polling_body["response"]["details"]["target_result"]["response"]["accepted_count"] == 2

    wms_example = await client.get("/api/training/examples/training.wms.shipment_fact_to_onec")
    assert wms_example.status_code == 200, wms_example.text
    assert wms_example.json()["endpoint_slug"] == "training-wms-shipment-fact-to-onec"

    wms_run = await client.post("/api/training/examples/training.wms.shipment_fact_to_onec/run")
    assert wms_run.status_code == 200, wms_run.text
    assert wms_run.json()["requires_setup"] is False
    assert wms_run.json()["success"] is True

    rejected = await client.post("/api/training/examples/training.errors.dnp_rejected/run")
    assert rejected.status_code == 200, rejected.text
    rejected_body = rejected.json()
    assert rejected_body["success"] is False
    assert rejected_body["timeline_url"].startswith("/events/")

    console = await client.post("/api/training/examples/training.onec.print_label/open-test-console")
    assert console.status_code == 200, console.text
    assert console.json()["url"] == "/test-console?trainingExampleId=training.onec.print_label"

    reset = await client.post("/api/training/reset")
    assert reset.status_code == 200, reset.text
    assert reset.json()["reset"] is True
    status_reset = await client.get("/api/training/status")
    assert status_reset.json()["sandbox_installed"] is False
