import pytest

from app.connectors.models import ConnectorInstance
from app.core.database import async_session
from app.odata_master.examples import DNP_CHZ_CODE_POOL_SYNC, LOOKUP_JSON_RESPONSE, LOOKUP_XML_RESPONSE

pytestmark = pytest.mark.asyncio

ORDER_REF = "c3335ee4-43d0-11f1-8388-000c29b755c7"
PRODUCT_REF = "ff22288c-2da4-11f1-8388-000c29b755c7"


async def install_onec_package(client):
    installed = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert installed.status_code == 200, installed.text


async def seed_chz_connector():
    object_resource_template = "Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция"
    object_resource_runtime = f"Document_ЗаказНаПроизводство2_2(guid'{ORDER_REF}')/Продукция"
    async with async_session() as session:
        session.add(
            ConnectorInstance(
                name="1C CHZ OData ERP",
                connector_type="onec",
                direction="target",
                enabled=True,
                status="enabled",
                config_json={
                    "base_url": "http://mock-1c.local/odata/standard.odata",
                    "auth": {"type": "none"},
                    "odata": {"enabled": True, "default_page_size": 100, "max_pages": 3},
                    "mock_odata": {
                        "Document_ЗаказНаПроизводство2_2": [
                            {"Ref_Key": ORDER_REF, "Number": "260666/6938", "Date": "2026-04-29T16:38:53", "Posted": True}
                        ],
                        object_resource_template: [
                            {"Номенклатура_Key": PRODUCT_REF, "Количество": 180, "КоличествоУпаковок": 180}
                        ],
                        object_resource_runtime: [
                            {"Номенклатура_Key": PRODUCT_REF, "Количество": 180, "КоличествоУпаковок": 180}
                        ],
                        "InformationRegister_ПулКодовМаркировкиСУЗ": [
                            {"КодМаркировки": "code-1", "ПолныйКодМаркировки": "full-code-1", "GTIN": "04601234567890", "Номенклатура_Key": PRODUCT_REF, "ДокументОснование": ORDER_REF},
                            {"КодМаркировки": "code-2", "ПолныйКодМаркировки": "full-code-2", "GTIN": "04601234567890", "Номенклатура_Key": PRODUCT_REF, "ДокументОснование": ORDER_REF},
                        ],
                    },
                },
            )
        )
        await session.commit()


async def test_odata_master_examples_and_preview_accept_dnp_spec(client):
    await install_onec_package(client)
    await seed_chz_connector()

    examples = await client.get("/api/odata-master/examples")
    assert examples.status_code == 200, examples.text
    assert {item["key"] for item in examples.json()} >= {"dnp_chz_code_pool_sync", "external_api_odata_json", "external_api_odata_xml"}

    response = await client.post("/api/odata-master/preview", json={"spec": DNP_CHZ_CODE_POOL_SYNC, "run_real_queries": False})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["validation"]["valid"] is True
    steps = body["builder_json"]["steps"]
    foreach = next(step for step in steps if step["type"] == "foreach")
    assert foreach["items"] == "products"
    assert foreach["step"]["top"] == 500
    assert foreach["step"]["paginate"] is True
    assert body["preview"]["valid"] is True
    assert body["preview"]["target_request_preview"]["body"]["payload"]["rows"][0]["ПолныйКодМаркировки"] == "full-code-1"


async def test_odata_master_rejects_top_above_500(client):
    await install_onec_package(client)
    spec = {**LOOKUP_JSON_RESPONSE, "steps": [{**LOOKUP_JSON_RESPONSE["steps"][0], "top": 501}]}

    response = await client.post("/api/odata-master/preview", json={"spec": spec})

    assert response.status_code == 400
    assert "$top не может быть больше 500" in response.json()["detail"]


async def test_odata_master_json_response_preserves_arrays_and_saves_flow(client):
    await install_onec_package(client)
    await seed_chz_connector()

    preview = await client.post("/api/odata-master/preview", json={"spec": LOOKUP_JSON_RESPONSE})
    assert preview.status_code == 200, preview.text
    return_step = preview.json()["preview"]["steps"][-1]
    assert return_step["result_preview"]["body"]["products"][0]["Номенклатура_Key"] == PRODUCT_REF

    saved = await client.post("/api/odata-master/save", json={"spec": LOOKUP_JSON_RESPONSE})
    assert saved.status_code == 200, saved.text
    saved_body = saved.json()
    assert saved_body["endpoint_url"] == "/api/bus/in/lookup_order_products"
    assert saved_body["integration_flow"]["compiled_workflow_id"]
    assert saved_body["next_steps"][0].startswith("Отправьте тестовый запрос")

    tested = await client.post("/api/odata-master/run-test", json={"flow_id": saved_body["integration_flow"]["id"]})
    assert tested.status_code == 200, tested.text
    tested_body = tested.json()
    result = tested_body["result"]
    assert result["bus_response"]["status"] == "completed"
    assert result["bus_response"]["response"]["products"][0]["Количество"] == 180
    diagnostics = tested_body["diagnostics"]
    assert diagnostics["event_id"] == result["bus_response"]["event_id"]
    assert diagnostics["timeline_url"] == result["bus_response"]["timeline_url"]
    artifact_names = {name for item in diagnostics["artifact_checklist"] for name in item["artifacts"]}
    assert {"odata_query_request.json", "odata_query_response.json", "return_response.json"} <= artifact_names
    assert any("Replay" in action or "Dry Run" in action for action in diagnostics["next_actions"])


async def test_odata_master_xml_response_template(client):
    await install_onec_package(client)
    await seed_chz_connector()

    response = await client.post("/api/odata-master/preview", json={"spec": LOOKUP_XML_RESPONSE})

    assert response.status_code == 200, response.text
    return_step = response.json()["preview"]["steps"][-1]
    assert return_step["request_preview"]["response_body_type"] == "xml"
    assert "<OrderNumber>260666/6938</OrderNumber>" in return_step["result_preview"]["body"]
