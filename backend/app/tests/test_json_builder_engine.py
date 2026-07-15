import pytest

from app.json_builder.engine import build_json_from_fields, build_json_from_template


def test_build_json_from_template_renders_object():
    result = build_json_from_template({"id": "{{ order.id }}", "static": 1}, {"order": {"id": 42}})
    assert result == {"id": 42, "static": 1}


def test_build_json_from_template_requires_object_result():
    with pytest.raises(ValueError, match="must render to an object"):
        build_json_from_template("{{ order.id }}", {"order": {"id": 42}})


def test_build_json_from_fields_constant_path_and_template_modes():
    fields = [
        {"target": "meta.source", "mode": "constant", "value": "erp"},
        {"target": "order.id", "mode": "path", "value": "request.body.id"},
        {"target": "order.label", "mode": "template", "value": "order-{{ request.body.id }}"},
    ]
    scope = {"request": {"body": {"id": 7}}}
    result = build_json_from_fields(fields, scope)
    assert result == {"meta": {"source": "erp"}, "order": {"id": 7, "label": "order-7"}}


def test_build_json_from_fields_default_mode_is_path():
    result = build_json_from_fields([{"target": "x", "value": "src.v"}], {"src": {"v": 9}})
    assert result == {"x": 9}


def test_build_json_from_fields_applies_transforms():
    fields = [{"target": "qty", "mode": "path", "value": "raw", "transforms": [{"name": "to_int"}]}]
    result = build_json_from_fields(fields, {"raw": " 12 "})
    assert result == {"qty": 12}


def test_build_json_from_fields_transform_failure_raises():
    fields = [{"target": "x", "mode": "constant", "value": "abc", "transforms": [{"name": "to_int"}]}]
    with pytest.raises(ValueError):
        build_json_from_fields(fields, {})


def test_build_json_from_fields_unknown_transform_raises():
    fields = [{"target": "x", "mode": "constant", "value": "abc", "transforms": [{"name": "missing"}]}]
    with pytest.raises(ValueError, match="not found"):
        build_json_from_fields(fields, {})


def test_build_json_from_fields_missing_target_raises():
    with pytest.raises(ValueError, match="target is required"):
        build_json_from_fields([{"target": "", "mode": "constant", "value": 1}], {})


def test_build_json_from_fields_path_collision_raises():
    fields = [
        {"target": "a", "mode": "constant", "value": 1},
        {"target": "a.b", "mode": "constant", "value": 2},
    ]
    with pytest.raises(ValueError, match="collides with non-object value"):
        build_json_from_fields(fields, {})
