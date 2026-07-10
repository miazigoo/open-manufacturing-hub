import os


async def test_onec_marking_code_pool_export_saves_file_with_real_gs(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "source_system": "1C ERP",
            "source_document_id": "AEAE-000137",
            "source_document_name": "Заказ на эмиссию AEAE-000137",
            "order_number": "260703/5442",
            "codes": [
                "0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU",
                "0104646151697186215_3IKhK1tdUba4f<+5IZ{GS}93d6Ba",
            ],
            "metadata_json": {"product": "power-supply"},
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["export"]["file_name"] == "260703_5442___2_pic.txt"
    file_path = tmp_path / payload["export"]["file_name"]
    assert file_path.exists()
    data = file_path.read_bytes()
    assert b"{GS}" not in data
    assert bytes([29]) in data
    assert data.count(bytes([29])) == 2
    assert data.startswith(b"010464")
    assert b"\xef\xbb\xbf" not in data[:3]
    assert len(data.splitlines()) == 2
    assert payload["export"]["total_codes"] == 2
    assert payload["export"]["status"] == "saved"
    get_settings.cache_clear()


async def test_onec_marking_code_pool_export_rejects_duplicate_codes(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "order_number": "260703/5442",
            "codes": [
                "0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU",
                "0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU",
            ],
        },
    )

    assert response.status_code == 400
    assert "Duplicate code" in response.json()["detail"]
    assert os.listdir(tmp_path) == []
    get_settings.cache_clear()
