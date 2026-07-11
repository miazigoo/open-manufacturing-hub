import base64
import os

from app.marking_code_pools.service import _default_file_name


def _full_code_base64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


async def test_onec_marking_code_pool_export_saves_base64_full_codes_with_real_gs(client, tmp_path, monkeypatch):
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
            "full_codes_base64": [
                _full_code_base64(b"0104646151697186215_<qlk<ZbCWFP>W2)foU" + bytes([29]) + b"93lzhU"),
                _full_code_base64(b"0104646151697186215_3IKhK1tdUba4f<+5IZ" + bytes([29]) + b"93d6Ba"),
            ],
            "metadata_json": {"product": "power-supply"},
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["export"]["file_name"] == "KM_260703-5442___2_pcs.txt"
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


async def test_onec_marking_code_pool_export_keeps_legacy_marker_codes_for_tests(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "order_number": "260703/5442",
            "codes": ["0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU"],
        },
    )

    assert response.status_code == 200, response.text
    data = (tmp_path / response.json()["export"]["file_name"]).read_bytes()
    assert bytes([29]) in data
    assert b"{GS}" not in data
    get_settings.cache_clear()


def test_marking_code_pool_default_file_name_matches_laser_format():
    assert _default_file_name("260891/4450", 4070) == "KM_260891-4450___4 070_pcs.txt"


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


async def test_onec_marking_code_pool_export_forwards_base64_pool_to_dnp(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    monkeypatch.setenv(
        "OMH_DNP_CHZ_CODE_POOL_IMPORT_URL",
        "http://dnp.local/api/v2/integrations/omh/chz/code-pools/from-1c",
    )
    monkeypatch.setenv("OMH_DNP_SHARED_SECRET", "secret-token")
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()
    calls = []

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "ok": True,
                "sync_run_id": 10,
                "order_1c_number": "260703/5442",
                "order_dnp_name": "26-0703/5442",
                "order_id": 99,
                "rows_count": 1,
                "created_count": 1,
                "updated_count": 0,
                "errors_count": 0,
                "errors": [],
            }

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            calls.append({"url": url, "json": json, "headers": headers, "timeout": self.timeout})
            return FakeResponse()

    monkeypatch.setattr(service.httpx, "AsyncClient", FakeAsyncClient)

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    code_b64 = _full_code_base64(
        b"0104646151697186215_<qlk<ZbCWFP>W2)foU" + bytes([29]) + b"93lzhU"
    )
    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "source_system": "1C ERP",
            "source_document_id": "AEAE-000137",
            "source_document_name": "Заказ на эмиссию AEAE-000137",
            "order_number": "260703/5442",
            "full_codes_base64": [code_b64],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["export"]["status"] == "forwarded"
    assert body["dnp_forward"]["order_dnp_name"] == "26-0703/5442"
    assert calls == [
        {
            "url": "http://dnp.local/api/v2/integrations/omh/chz/code-pools/from-1c",
            "headers": {
                "Content-Type": "application/json",
                "X-OMH-Token": "secret-token",
            },
            "timeout": 180.0,
            "json": {
                "omh": {
                    "event_id": body["export"]["id"],
                    "correlation_id": f"chz-code-pool:260703/5442:{body['export']['id']}",
                    "event_type": "ChestniyZnakCodePoolPushedFrom1C",
                    "entity_type": "OneCMarkingCodePool",
                    "entity_id": "AEAE-000137",
                    "source_system": "Open Manufacturing Hub",
                    "target_system": "DnP",
                    "sent_at": calls[0]["json"]["omh"]["sent_at"],
                },
                "payload": {
                    "source_system": "1C ERP",
                    "source_document_id": "AEAE-000137",
                    "source_document_name": "Заказ на эмиссию AEAE-000137",
                    "order_number": "260703/5442",
                    "file_name": "KM_260703-5442___1_pcs.txt",
                    "total_codes": 1,
                    "content_sha256": body["export"]["content_sha256"],
                    "full_codes_base64": [code_b64],
                    "metadata_json": {},
                },
            },
        }
    ]
    get_settings.cache_clear()


async def test_onec_marking_code_pool_export_keeps_dnp_forward_when_laser_share_fails(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    monkeypatch.setenv(
        "OMH_DNP_CHZ_CODE_POOL_IMPORT_URL",
        "http://dnp.local/api/v2/integrations/omh/chz/code-pools/from-1c",
    )
    monkeypatch.setenv("OMH_CHZ_LASER_SMB_UNC", r"\\172.16.8.133\DataMatrixCodes")
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()
    calls = []

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {
                "ok": True,
                "sync_run_id": 11,
                "order_1c_number": "260703/5442",
                "order_dnp_name": "26-0703/5442",
                "order_id": 99,
                "rows_count": 1,
                "created_count": 0,
                "updated_count": 1,
                "errors_count": 0,
                "errors": [],
            }

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            calls.append({"url": url, "json": json, "headers": headers, "timeout": self.timeout})
            return FakeResponse()

    def fail_laser_write(*args, **kwargs):
        raise OSError("Host is down")

    monkeypatch.setattr(service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(service, "_write_smb_file", fail_laser_write)

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    code_b64 = _full_code_base64(
        b"0104646151697186215_<qlk<ZbCWFP>W2)foU" + bytes([29]) + b"93lzhU"
    )
    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "source_system": "1C ERP",
            "source_document_id": "AEAE-000137",
            "source_document_name": "Заказ на эмиссию AEAE-000137",
            "order_number": "260703/5442",
            "full_codes_base64": [code_b64],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["export"]["status"] == "partial_success"
    assert body["actions"]["local_outbox"]["status"] == "success"
    assert body["actions"]["laser_file"]["status"] == "failed"
    assert "Host is down" in body["actions"]["laser_file"]["error"]
    assert body["actions"]["dnp_forward"]["status"] == "success"
    assert body["dnp_forward"]["updated_count"] == 1
    assert calls
    get_settings.cache_clear()
