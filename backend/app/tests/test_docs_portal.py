async def test_docs_index_packages_and_page(client):
    index_response = await client.get("/api/docs/index?lang=ru")
    assert index_response.status_code == 200, index_response.text
    index = index_response.json()
    assert index["language"] == "ru"
    assert index["packages"][0]["id"] == "core"
    assert any(package["id"] == "onec" for package in index["packages"])

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
