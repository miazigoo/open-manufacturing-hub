from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.execution.steps.flow_builder_steps import _marking_code_pool_request


@pytest.mark.parametrize(
    ("destination", "expected_laser_file"),
    [
        ("print", False),
        ("PRINT", False),
        ("laser", None),
        ("not_specified", None),
        ("", None),
    ],
)
def test_marking_pool_destination_controls_laser_copy(destination, expected_laser_file):
    payload = {
        "order_number": "261095/6811",
        "full_codes_base64": ["MDEwNDY0NjE1MTY5NzE4NjIxNVQxMjM="],
        "destination": destination,
    }
    config = {
        "step_id": "deliver_chz_pool",
        "order_number_path": "request.body.order_number",
        "full_codes_base64_path": "request.body.full_codes_base64",
        "destination_path": "request.body.destination",
    }
    context = SimpleNamespace(
        event=SimpleNamespace(id=uuid4()),
        run=SimpleNamespace(id=uuid4()),
        source_system="1C ERP",
    )

    request = _marking_code_pool_request(config, {"request": {"body": payload}}, context)

    assert request.actions_override is not None
    assert request.actions_override.laser_file is expected_laser_file
