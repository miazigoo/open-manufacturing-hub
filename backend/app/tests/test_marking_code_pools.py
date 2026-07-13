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


async def test_onec_chz_pool_delivery_flow_endpoint_is_visible_and_executable(client, tmp_path, monkeypatch):
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
                "sync_run_id": 12,
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

    installed = await client.post("/api/scenario-library/onec_chz_pool_delivery/install")
    assert installed.status_code == 200, installed.text
    assert installed.json()["endpoint_url"] == "/api/bus/in/onec-chz-pool-delivery"

    flows = await client.get("/api/integration-flows")
    assert flows.status_code == 200, flows.text
    flow = next(item for item in flows.json() if item["slug"] == "onec-chz-pool-delivery")
    assert flow["builder_json"]["steps"][0]["type"] == "marking_code_pool_export"
    assert "/api/bus/in/onec-chz-pool-delivery" in flow["onec_http_example"]

    code_b64 = _full_code_base64(
        b"0104646151697186215_<qlk<ZbCWFP>W2)foU" + bytes([29]) + b"93lzhU"
    )
    response = await client.post(
        "/api/bus/in/onec-chz-pool-delivery",
        json={
            "source_document_id": "AEAE-000137",
            "source_document_name": "Заказ на эмиссию AEAE-000137",
            "order_number": "260703/5442",
            "full_codes_base64": [code_b64],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["event_id"]
    result = body["response"]
    assert result["success"] is True
    assert result["status"] == "forwarded"
    assert result["export"]["file_name"] == "KM_260703-5442___1_pcs.txt"
    assert result["actions"]["local_outbox"]["status"] == "success"
    assert result["actions"]["dnp_forward"]["status"] == "success"
    assert calls[0]["json"]["payload"]["full_codes_base64"] == [code_b64]
    assert (tmp_path / "KM_260703-5442___1_pcs.txt").exists()

    timeline = await client.get(f"/api/events/{body['event_id']}/timeline")
    assert timeline.status_code == 200, timeline.text
    artifacts = [
        artifact["name"]
        for run in timeline.json()["runs"]
        for step in run["steps"]
        for artifact in step["artifacts"]
    ]
    assert "marking_code_pool_export_actions.json" in artifacts
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


async def test_marking_code_pool_settings_get_patch_and_local_dir_test(client, tmp_path):
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    initial = await client.get("/api/marking-code-pools/settings")
    assert initial.status_code == 200, initial.text
    assert initial.json()["local_outbox"]["required"] is True

    export_dir = tmp_path / "exports"
    patched = await client.patch(
        "/api/marking-code-pools/settings",
        json={
            "export_dir": str(export_dir),
            "file_name_template": "KM_{{order_number_safe}}___{{total_codes}}_pcs.txt",
            "laser_enabled": True,
            "laser_smb_unc": r"\\172.16.8.133\DataMatrixCodes",
            "laser_smb_username": "laser-user",
            "laser_smb_password": "laser-password",
            "forward_enabled": True,
            "forward_service_name": "DnP",
            "forward_url": "http://dnp.local/import",
            "forward_token": "secret-token",
            "forward_timeout_seconds": 15,
            "response_success_mode": "partial_success_allowed",
        },
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["source"] == "current_environment"
    assert body["local_outbox"]["export_dir"] == str(export_dir)
    assert body["laser"]["enabled"] is True
    assert body["laser"]["password_set"] is True
    assert body["forward"]["enabled"] is True
    assert body["forward"]["token_set"] is True
    assert body["forward"]["timeout_seconds"] == 15

    local_test = await client.post("/api/marking-code-pools/settings/test-local-dir")
    assert local_test.status_code == 200, local_test.text
    assert local_test.json()["success"] is True
    assert export_dir.exists()


async def test_marking_code_pool_preview_validates_base64_without_writing(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file/preview",
        json={
            "source_system": "1C ERP",
            "order_number": "260703/5442",
            "full_codes_base64": [
                _full_code_base64(b"0104646151697186215_<qlk<ZbCWFP>W2)foU" + bytes([29]) + b"93lzhU")
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["file_name"] == "KM_260703-5442___1_pcs.txt"
    assert body["total_codes"] == 1
    assert body["would_save_to"] == str(tmp_path / "KM_260703-5442___1_pcs.txt")
    assert os.listdir(tmp_path) == []
    get_settings.cache_clear()


async def test_marking_code_pool_preview_validates_legacy_marker_without_writing(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file/preview",
        json={
            "order_number": "260703/5442",
            "codes": ["0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU"],
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["content_sha256"]
    assert os.listdir(tmp_path) == []
    get_settings.cache_clear()


async def test_marking_code_pool_download_returns_file_and_missing_returns_404(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    from app.core.config import get_settings

    get_settings.cache_clear()
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    export = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "order_number": "260703/5442",
            "codes": ["0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU"],
        },
    )
    assert export.status_code == 200, export.text
    export_id = export.json()["export"]["id"]
    file_name = export.json()["export"]["file_name"]

    download = await client.get(f"/api/marking-code-pools/exports/{export_id}/download")
    assert download.status_code == 200, download.text
    assert download.headers["content-type"].startswith("text/plain")
    assert bytes([29]) in download.content
    assert "filename" in download.headers["content-disposition"]

    changed_dir = tmp_path / "changed-export-dir"
    settings = await client.patch("/api/marking-code-pools/settings", json={"export_dir": str(changed_dir)})
    assert settings.status_code == 200, settings.text
    download_after_dir_change = await client.get(f"/api/marking-code-pools/exports/{export_id}/download")
    assert download_after_dir_change.status_code == 200, download_after_dir_change.text
    assert download_after_dir_change.content == download.content

    (tmp_path / file_name).unlink()
    missing = await client.get(f"/api/marking-code-pools/exports/{export_id}/download")
    assert missing.status_code == 404
    get_settings.cache_clear()


async def test_marking_code_pool_settings_test_forward_can_be_mocked(client, monkeypatch):
    monkeypatch.setenv("OMH_DNP_CHZ_CODE_POOL_IMPORT_URL", "http://dnp.local/import")
    monkeypatch.setenv("OMH_DNP_SHARED_SECRET", "secret-token")
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()
    calls = []

    class FakeResponse:
        status_code = 200
        text = '{"ok": true}'

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

    response = await client.post(
        "/api/marking-code-pools/settings/test-forward",
        json={"send_test_request": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["success"] is True
    assert calls[0]["url"] == "http://dnp.local/import"
    assert calls[0]["headers"]["X-OMH-Token"] == "secret-token"
    assert calls[0]["json"]["omh_test"] is True
    get_settings.cache_clear()


async def test_marking_code_pool_allow_overwrite_default_applies_when_request_omits_flag(client, tmp_path):
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    settings = await client.patch(
        "/api/marking-code-pools/settings",
        json={"export_dir": str(tmp_path), "allow_overwrite_default": False},
    )
    assert settings.status_code == 200, settings.text

    payload = {
        "order_number": "260703/5442",
        "codes": ["0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU"],
    }
    first = await client.post("/api/marking-code-pools/onec/export-file", json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["export"]["status"] == "saved"

    second = await client.post("/api/marking-code-pools/onec/export-file", json=payload)
    assert second.status_code == 200, second.text
    assert second.json()["export"]["status"] == "failed"
    assert "already exists" in second.json()["actions"]["local_outbox"]["error"]


async def test_marking_code_pool_action_override_skips_global_laser_and_forward(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    monkeypatch.setenv("OMH_CHZ_LASER_SMB_UNC", r"\\172.16.8.133\DataMatrixCodes")
    monkeypatch.setenv("OMH_DNP_CHZ_CODE_POOL_IMPORT_URL", "http://dnp.local/import")
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()
    smb_calls = []
    forward_calls = []

    def fake_smb_write(*args, **kwargs):
        smb_calls.append({"args": args, "kwargs": kwargs})

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            forward_calls.append({"url": url, "json": json, "headers": headers})
            raise AssertionError("forward must be skipped by actions_override")

    monkeypatch.setattr(service, "_write_smb_file", fake_smb_write)
    monkeypatch.setattr(service.httpx, "AsyncClient", FakeAsyncClient)

    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "order_number": "260703/5442",
            "codes": ["0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU"],
            "actions_override": {"laser_file": False, "external_forward": False},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "saved"
    assert body["actions"]["laser_file"]["status"] == "disabled"
    assert body["actions"]["laser_file"]["reason"] == "disabled by this test action"
    assert body["actions"]["external_forward"]["status"] == "disabled"
    assert body["actions"]["external_forward"]["reason"] == "disabled by this test action"
    assert body["actions"]["dnp_forward"]["status"] == "disabled"
    assert smb_calls == []
    assert forward_calls == []
    get_settings.cache_clear()


async def test_marking_code_pool_preview_reflects_action_override_reasons(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    monkeypatch.setenv("OMH_CHZ_LASER_SMB_UNC", r"\\172.16.8.133\DataMatrixCodes")
    monkeypatch.setenv("OMH_DNP_CHZ_CODE_POOL_IMPORT_URL", "http://dnp.local/import")
    from app.core.config import get_settings

    get_settings.cache_clear()
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file/preview",
        json={
            "order_number": "260703/5442",
            "codes": ["0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU"],
            "actions_override": {"laser_file": False, "external_forward": False},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["would_laser_copy"]["enabled"] is False
    assert body["would_laser_copy"]["reason"] == "disabled by this test action"
    assert body["would_forward"]["enabled"] is False
    assert body["would_forward"]["reason"] == "disabled by this test action"
    assert body["warnings"] == []
    assert os.listdir(tmp_path) == []
    get_settings.cache_clear()


async def test_marking_code_pool_response_success_false_when_forward_required_and_fails(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    monkeypatch.setenv("OMH_DNP_CHZ_CODE_POOL_IMPORT_URL", "http://dnp.local/import")
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_RESPONSE_SUCCESS_MODE", "local_file_and_forward_success")
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            raise service.httpx.ConnectError("connection refused")

    monkeypatch.setattr(service.httpx, "AsyncClient", FakeAsyncClient)
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    response = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "order_number": "260703/5442",
            "codes": ["0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU"],
            "actions_override": {"external_forward": True, "laser_file": False},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is False
    assert body["status"] == "partial_success"
    assert body["export"]["status"] == "partial_success"
    assert body["actions"]["external_forward"]["status"] == "failed"
    assert "connection refused" in body["warnings"][0]
    get_settings.cache_clear()


async def test_marking_code_pool_retry_forward_reads_saved_file_and_updates_metadata(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    monkeypatch.setenv("OMH_DNP_CHZ_CODE_POOL_IMPORT_URL", "http://dnp.local/import")
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()
    calls = []

    class FakeResponse:
        status_code = 200
        text = '{"ok": true}'

        @staticmethod
        def json():
            return {"ok": True, "updated_count": 1}

    class FakeAsyncClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            calls.append({"url": url, "json": json, "headers": headers})
            return FakeResponse()

    monkeypatch.setattr(service.httpx, "AsyncClient", FakeAsyncClient)
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    code_b64 = _full_code_base64(b"0104646151697186215_<qlk<ZbCWFP>W2)foU" + bytes([29]) + b"93lzhU")
    export = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "order_number": "260703/5442",
            "full_codes_base64": [code_b64],
            "actions_override": {"external_forward": False, "laser_file": False},
        },
    )
    assert export.status_code == 200, export.text
    assert calls == []

    retry = await client.post(f"/api/marking-code-pools/exports/{export.json()['export']['id']}/retry-forward")
    assert retry.status_code == 200, retry.text
    assert retry.json()["success"] is True
    assert calls[0]["url"] == "http://dnp.local/import"
    assert calls[0]["json"]["payload"]["full_codes_base64"] == [code_b64]

    details = await client.get(f"/api/marking-code-pools/exports/{export.json()['export']['id']}")
    assert details.status_code == 200, details.text
    assert details.json()["status"] == "forwarded"
    assert details.json()["forwarded_at"] is not None
    assert details.json()["metadata_json"]["actions"]["external_forward"]["status"] == "success"
    assert details.json()["metadata_json"]["actions"]["dnp_forward"]["status"] == "success"
    get_settings.cache_clear()


async def test_marking_code_pool_retry_laser_copy_and_missing_file_response(client, tmp_path, monkeypatch):
    monkeypatch.setenv("OMH_MARKING_CODE_POOL_EXPORT_DIR", str(tmp_path))
    monkeypatch.setenv("OMH_CHZ_LASER_SMB_UNC", r"\\172.16.8.133\DataMatrixCodes")
    from app.core.config import get_settings
    from app.marking_code_pools import service

    get_settings.cache_clear()
    smb_calls = []

    def fake_smb_write(
        unc_dir,
        file_name,
        payload,
        *,
        username,
        password,
        require_signing,
        require_secure_negotiate,
    ):
        smb_calls.append(
            {
                "unc_dir": unc_dir,
                "file_name": file_name,
                "payload": payload,
                "username": username,
                "password": password,
                "require_signing": require_signing,
                "require_secure_negotiate": require_secure_negotiate,
            }
        )

    monkeypatch.setattr(service, "_write_smb_file", fake_smb_write)
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text

    export = await client.post(
        "/api/marking-code-pools/onec/export-file",
        json={
            "order_number": "260703/5442",
            "codes": ["0104646151697186215_<qlk<ZbCWFP>W2)foU{GS}93lzhU"],
            "actions_override": {"laser_file": False, "external_forward": False},
        },
    )
    assert export.status_code == 200, export.text
    export_id = export.json()["export"]["id"]
    file_name = export.json()["export"]["file_name"]

    retry = await client.post(f"/api/marking-code-pools/exports/{export_id}/retry-laser-copy")
    assert retry.status_code == 200, retry.text
    assert retry.json()["success"] is True
    assert smb_calls[0]["file_name"] == file_name
    assert bytes([29]) in smb_calls[0]["payload"]

    (tmp_path / file_name).unlink()
    missing = await client.post(f"/api/marking-code-pools/exports/{export_id}/retry-forward")
    assert missing.status_code == 200, missing.text
    assert missing.json()["success"] is False
    assert missing.json()["error_code"] == "EXPORT_FILE_NOT_FOUND"
    get_settings.cache_clear()
