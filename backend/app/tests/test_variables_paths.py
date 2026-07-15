import pytest

from app.variables.paths import PathResolutionError, resolve_path, try_resolve_path


def test_resolve_path_nested_dict_and_list_index():
    data = {"order": {"items": [{"sku": "A"}, {"sku": "B"}]}}
    assert resolve_path(data, "order.items[1].sku") == "B"


def test_resolve_path_length_on_list_dict_and_string():
    assert resolve_path([1, 2, 3], "length") == 3
    assert resolve_path({"s": "abcd"}, "s.length") == 4
    assert resolve_path({"a": 1, "b": 2}, "length") == 2


def test_resolve_path_length_key_takes_precedence_when_present():
    assert resolve_path({"length": "explicit"}, "length") == "explicit"


def test_resolve_path_empty_path_raises():
    with pytest.raises(PathResolutionError) as excinfo:
        resolve_path({"a": 1}, "")
    assert excinfo.value.message == "Path is empty"
    assert "resolving ''" in str(excinfo.value)


def test_resolve_path_none_path_raises():
    with pytest.raises(PathResolutionError):
        resolve_path({"a": 1}, None)


def test_resolve_path_missing_key_raises():
    with pytest.raises(PathResolutionError) as excinfo:
        resolve_path({"a": 1}, "b")
    assert excinfo.value.segment == "b"
    assert excinfo.value.message == "Key not found"


def test_resolve_path_index_on_non_list_raises():
    with pytest.raises(PathResolutionError) as excinfo:
        resolve_path({"a": 1}, "a[0]")
    assert excinfo.value.message == "Expected list"


def test_resolve_path_index_out_of_range_raises():
    with pytest.raises(PathResolutionError) as excinfo:
        resolve_path([1, 2], "[5]")
    assert excinfo.value.message == "List index is out of range"


def test_resolve_path_key_on_non_object_raises():
    with pytest.raises(PathResolutionError) as excinfo:
        resolve_path({"a": 5}, "a.b")
    assert excinfo.value.message == "Expected object"


def test_resolve_path_length_on_unsupported_type_raises():
    with pytest.raises(PathResolutionError) as excinfo:
        resolve_path({"n": 5}, "n.length")
    assert excinfo.value.message == "Expected list, object or string"


def test_resolve_path_invalid_syntax_raises():
    with pytest.raises(PathResolutionError):
        resolve_path({"a": [1]}, "a!b")


def test_try_resolve_path_returns_value_when_present():
    assert try_resolve_path({"a": {"b": 7}}, "a.b") == 7


def test_try_resolve_path_returns_default_on_error():
    assert try_resolve_path({}, "a.b", default="fallback") == "fallback"


def test_try_resolve_path_default_is_none_by_default():
    assert try_resolve_path({}, "missing") is None
