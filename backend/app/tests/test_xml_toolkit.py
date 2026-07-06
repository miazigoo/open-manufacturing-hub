from __future__ import annotations

from app.flow_builder.compiler import FlowCompiler


async def test_xml_toolkit_parse_extract_render_and_raw_preview(client):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Request>
  <Operation>lookup_order_products</Operation>
  <Number>260666/6938</Number>
  <DeviceType>toodoo</DeviceType>
  <Lines><Line><Sku>A1</Sku></Line><Line><Sku>B2</Sku></Line></Lines>
</Request>"""

    parsed = await client.post("/api/xml-toolkit/parse", json={"xml": xml})
    assert parsed.status_code == 200, parsed.text
    body = parsed.json()
    assert body["success"] is True
    assert body["root"] == "Request"
    assert body["encoding_detected"] == "UTF-8"
    assert {item["path"] for item in body["paths"]} >= {"/Request/Number", "/Request/DeviceType", "/Request/Lines/Line[0]/Sku", "/Request/Lines/Line[1]/Sku"}

    extracted = await client.post(
        "/api/xml-toolkit/extract",
        json={"xml": xml, "fields": [{"name": "number", "path": "/Request/Number", "required": True}, {"name": "skus", "path": "/Request/Lines/Line/Sku", "mode": "all"}]},
    )
    assert extracted.status_code == 200, extracted.text
    assert extracted.json()["success"] is True
    assert extracted.json()["values"] == {"number": "260666/6938", "skus": ["A1", "B2"]}

    rendered = await client.post(
        "/api/xml-toolkit/render",
        json={"template": "<Response><Number>{{number}}</Number><Unsafe>{{unsafe}}</Unsafe></Response>", "variables": {"number": "260666/6938", "unsafe": "A&B"}},
    )
    assert rendered.status_code == 200, rendered.text
    assert rendered.json()["success"] is True
    assert "<Unsafe>A&amp;B</Unsafe>" in rendered.json()["rendered"]

    missing = await client.post("/api/xml-toolkit/render", json={"template": "<Response>{{missing}}</Response>", "variables": {}})
    assert missing.status_code == 200
    assert missing.json()["success"] is False
    assert "missing" in missing.json()["errors"][0]

    raw = await client.post("/api/xml-toolkit/raw-forward-preview", json={"xml": xml})
    assert raw.status_code == 200
    assert raw.json()["forwarded_unchanged"] is True


async def test_flow_builder_preview_compiles_xml_extract_to_odata_and_xml_response(client):
    builder = {
        "version": 1,
        "input": {"endpoint_slug": "xml-lookup", "input_mode": "xml", "response_mode": "sync_response"},
        "steps": [
            {
                "id": "extract_xml_fields",
                "type": "xml_extract",
                "name": "Extract XML fields",
                "source": "request.xml",
                "fields": [{"name": "number", "path": "/Request/Number", "required": True}],
            },
            {
                "id": "get_order",
                "type": "odata_query",
                "name": "Find order",
                "connection": "Demo 1C ERP",
                "resource": "Document_ЗаказНаПроизводство2_2",
                "filter": "Number eq '{{number}}'",
                "select": ["Ref_Key", "Number"],
                "top": 1,
                "save_as": "order",
                "required": True,
                "mock_items": [{"Ref_Key": "order-001", "Number": "260666/6938"}],
            },
            {
                "id": "return_xml",
                "type": "build_xml_response",
                "name": "Return XML",
                "status_code": 200,
                "body_template": "<Response><Order>{{order.Ref_Key}}</Order><Number>{{number}}</Number></Response>",
            },
        ],
    }

    preview = await client.post("/api/flow-builder/preview", json={"builder_json": builder, "sample_request": {"xml": "<Request><Number>260666/6938</Number></Request>"}})

    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["valid"] is True
    assert body["variables"]["number"] == "260666/6938"
    assert body["steps"][1]["request_preview"]["query"]["$filter"] == "Number eq '260666/6938'"
    assert body["steps"][2]["result_preview"]["response_body_type"] == "xml"
    assert body["steps"][2]["result_preview"]["body"] == "<Response><Order>order-001</Order><Number>260666/6938</Number></Response>"

    compiled = FlowCompiler().compile(builder)
    assert compiled["valid"] is True
    assert compiled["steps_json"][0]["handler"] == "xml_extract"
    assert compiled["steps_json"][2]["handler"] == "flow_return_response"
    assert compiled["steps_json"][2]["config"]["response_body_type"] == "xml"
