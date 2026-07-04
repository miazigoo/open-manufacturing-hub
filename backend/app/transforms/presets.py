from __future__ import annotations

SMART_ROUTER_TRANSFORM_CHAINS = [
    {"source": "request.body.pool_type", "target": "payload.pool_type", "transforms": [{"name": "trim"}, {"name": "uppercase"}]},
    {"source": "request.body.inn", "target": "variables.normalized_inn", "transforms": [{"name": "trim"}, {"name": "remove_spaces"}]},
    {"source": "request.body.product_code", "target": "variables.normalized_product_code", "transforms": [{"name": "trim"}, {"name": "uppercase"}]},
]
