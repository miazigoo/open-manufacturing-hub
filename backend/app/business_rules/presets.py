from __future__ import annotations

SMART_ROUTER_RULE_SET = {
    "name": "1C Marking Pool Smart Router",
    "description": "Routes marking pool requests to DNP service or printer by normalized pool_type.",
    "enabled": True,
    "scope": "global",
    "rules_json": {
        "mode": "first_match",
        "rules": [
            {"name": "DNP pool", "if": {"path": "request.body.pool_type", "operator": "eq", "value": "DNP"}, "then": [{"action": "set_variable", "path": "variables.target_service", "value": "DNP Service"}, {"action": "set_operation", "value": "send_marking_pool"}]},
            {"name": "Print pool", "if": {"path": "request.body.pool_type", "operator": "eq", "value": "PRINT"}, "then": [{"action": "set_variable", "path": "variables.target_service", "value": "Label Printer"}, {"action": "set_operation", "value": "print_marking_pool"}]},
            {"name": "Unknown pool", "if": {"operator": "always"}, "then": [{"action": "fail", "error_code": "UNKNOWN_POOL_TYPE", "message": "Unknown pool type {{request.body.pool_type}}"}]},
        ],
    },
}
