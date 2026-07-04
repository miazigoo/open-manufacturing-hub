OPERATION_TEMPLATE_PRESETS = [
    {
        "name": "1C Receive UPD XML",
        "system_type": "onec",
        "operation": "receive_upd_xml",
        "description": "Send raw UPD XML to a 1C HTTP service endpoint.",
        "request_template_json": {"_omh": {"operation": "receive_upd_xml", "content_type": "application/xml"}, "xml": "{{xml_payload}}", "message_id": "{{message.id}}"},
        "response_schema_json": {"success": "boolean", "status": "string", "message": "string"},
    },
    {
        "name": "1C Lookup Contractor By INN",
        "system_type": "onec",
        "operation": "lookup_contractor_by_inn",
        "description": "Resolve contractor Ref_Key by INN via 1C OData.",
        "request_template_json": {"resource": "Catalog_Контрагенты", "filter_template": "ИНН eq '{inn}'", "extract": {"contractor_uuid": "Ref_Key"}},
    },
    {
        "name": "1C Update Shipment Status",
        "system_type": "onec",
        "operation": "update_shipment_status",
        "description": "Post shipment status facts back to 1C.",
        "request_template_json": {"_omh": {"operation": "update_shipment_status"}, "payload": "{{payload}}"},
    },
    {
        "name": "Print ZPL",
        "system_type": "printing",
        "operation": "print_zpl",
        "description": "Create/send a traceable ZPL print job through the printing service.",
        "request_template_json": {"job_key": "{{job_key}}", "printer": "{{printer}}", "lines": "{{lines}}", "dry_run": False},
    },
]
