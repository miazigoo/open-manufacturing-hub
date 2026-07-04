BUILDER_STEP_TYPES = {
    "read_variable": "Read value from inbound request/context",
    "odata_query": "Query 1C/OData and save the first row/items",
    "resolve_object": "Resolve a canonical Customer/Product/Warehouse/etc. through Resolver Engine v2",
    "build_json": "Build target JSON from variables and constants",
    "condition": "Fail or continue based on a simple condition",
    "call_endpoint": "Call REST/1C/API connector with built payload",
    "return_response": "Select synchronous response body",
}
