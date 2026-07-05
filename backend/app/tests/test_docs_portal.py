async def test_docs_index_packages_and_page(client):
    required_onec_page_ids = {
        "onec.overview.overview",
        "onec.setup.connector-setup",
        "onec.setup.auth-secrets-static-token",
        "onec.tools.connector",
        "onec.tools.odata-explorer",
        "onec.tools.xml-tools",
        "onec.tools.cockpit",
        "onec.tools.visual-flow-builder",
        "onec.scenarios.onec-to-external-api",
        "onec.scenarios.onec-post-two-odata-json-endpoint",
        "onec.scenarios.xml-raw-forward",
        "onec.scenarios.xml-inn-lookup",
        "onec.scenarios.onec-to-printer",
        "onec.scenarios.website-api-to-1c",
        "onec.scenarios.odata-polling-to-target",
        "onec.scenarios.wms-api-to-1c",
        "onec.support.errors-timeline-artifacts",
        "onec.support.queue-retry-dlq",
    }

    index_response = await client.get("/api/docs/index?lang=ru")
    assert index_response.status_code == 200, index_response.text
    index = index_response.json()
    assert index["language"] == "ru"
    assert index["packages"][0]["id"] == "core"
    assert any(package["id"] == "onec" for package in index["packages"])
    onec_package = next(package for package in index["packages"] if package["id"] == "onec")
    indexed_onec_page_ids = {page["id"] for section in onec_package["sections"] for page in section["pages"]}
    assert required_onec_page_ids <= indexed_onec_page_ids

    packages_response = await client.get("/api/docs/packages?lang=en")
    assert packages_response.status_code == 200, packages_response.text
    packages = packages_response.json()
    assert packages[0]["title"] == "Quick Start"

    page_response = await client.get("/api/docs/pages/onec.tools.odata-explorer?lang=zh")
    assert page_response.status_code == 200, page_response.text
    page = page_response.json()
    assert page["id"] == "onec.tools.odata-explorer"
    assert page["translation_status"] == "in_progress"
    assert page["route"] == "/docs/onec/tools/odata-explorer"


async def test_docs_export_pdf_contract_is_explicitly_not_ready(client):
    response = await client.get("/api/docs/export-pdf?lang=ru&package=onec")
    assert response.status_code == 501
    body = response.json()
    assert body["error"] == "DOCS_PDF_EXPORT_NOT_IMPLEMENTED"
    assert body["package_id"] == "onec"
    assert body["planned"] is True


async def test_docs_unknown_page_returns_404(client):
    response = await client.get("/api/docs/pages/missing.page")
    assert response.status_code == 404
