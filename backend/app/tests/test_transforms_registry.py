from datetime import datetime, timezone

from app.transforms.engine import engine
from app.transforms.registry import registry
from app.transforms.schemas import TransformStep


def apply(name, value, args=None):
    result = engine.apply_chain(value, [{"name": name, "args": args or {}}], {})
    assert result.success is True, result.error_message
    return result.value


def test_registry_get_and_list():
    assert registry.get("trim") is not None
    assert registry.get("does_not_exist") is None
    definitions = registry.list()
    names = {d.name for d in definitions}
    assert {"trim", "to_int", "date_format", "uuid", "coalesce"} <= names
    # list is sorted by (category, name)
    keys = [(d.category, d.name) for d in definitions]
    assert keys == sorted(keys)


def test_string_transforms():
    assert apply("trim", "  hi  ") == "hi"
    assert apply("trim", None) == ""
    assert apply("uppercase", "abc") == "ABC"
    assert apply("lowercase", "ABC") == "abc"
    assert apply("replace", "a b a", {"old": "a", "new": "x"}) == "x b x"
    assert apply("remove_spaces", "a b\tc\n") == "abc"
    assert apply("normalize_whitespace", "  a   b \n c ") == "a b c"
    assert apply("substring", "abcdef", {"start": 1, "end": 4}) == "bcd"
    assert apply("substring", "abcdef", {"start": 2}) == "cdef"
    assert apply("split", "a,b,c", {"separator": ","}) == ["a", "b", "c"]
    assert apply("join", ["a", "b"], {"separator": "-"}) == "a-b"
    assert apply("join", "solo", {"separator": "-"}) == "solo"
    assert apply("concat", "a", {"values": ["b", "c"]}) == "abc"
    assert apply("regex_replace", "a1b2", {"pattern": r"\d", "replacement": "#"}) == "a#b#"


def test_number_transforms():
    assert apply("to_int", " 42 ") == 42
    assert apply("to_int", "10.0") == 10
    assert apply("to_float", " 3.5 ") == 3.5
    assert apply("round", 3.14159, {"digits": 2}) == 3.14
    assert apply("abs", -7) == 7.0


def test_date_transforms():
    assert apply("date_parse", "2026-07-04T10:30:00Z") == "2026-07-04T10:30:00+00:00"
    assert apply("date_format", "2026-07-04T10:30:00Z", {"format": "%Y%m%d"}) == "20260704"
    now_value = apply("now", None)
    parsed = datetime.fromisoformat(now_value)
    assert parsed.tzinfo is not None


def test_date_parse_passthrough_datetime_and_empty():
    dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert apply("date_parse", dt) == dt.isoformat()
    # empty resolves to current time (just ensure it is parseable)
    datetime.fromisoformat(apply("date_parse", ""))


def test_technical_transforms():
    assert len(apply("uuid", None)) == 36
    assert apply("hash_sha256", "abc") == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    encoded = apply("base64_encode", "hello")
    assert encoded == "aGVsbG8="
    assert apply("base64_decode", encoded) == "hello"
    assert apply("json_stringify", {"b": 1, "a": 2}, {"sort_keys": True}) == '{"a": 2, "b": 1}'
    assert apply("json_parse", '{"x": 1}') == {"x": 1}
    assert apply("json_parse", None) is None
    assert apply("xml_escape", '<a & "b">') == "&lt;a &amp; &quot;b&quot;&gt;"
    assert apply("xml_unescape", "&lt;a&gt;") == "<a>"


def test_defaults_transforms():
    assert apply("default_value", "", {"default": "fallback"}) == "fallback"
    assert apply("default_value", "keep", {"default": "fallback"}) == "keep"
    assert apply("coalesce", None, {"values": ["", "first", "second"]}) == "first"
    assert apply("coalesce", "primary", {"values": ["other"]}) == "primary"
    assert apply("coalesce", None, {"values": []}) is None
    assert apply("empty_to_null", []) is None
    assert apply("empty_to_null", "x") == "x"
    assert apply("null_to_empty", None) == ""
    assert apply("null_to_empty", "x") == "x"


def test_apply_chain_records_trace_and_accepts_transform_step():
    result = engine.apply_chain("  abc ", [TransformStep(name="trim"), {"name": "uppercase"}], {})
    assert result.success is True
    assert result.value == "ABC"
    assert [item.transform for item in result.trace] == ["trim", "uppercase"]
    assert result.trace[0].before == "  abc "
    assert result.trace[0].after == "abc"


def test_apply_chain_unknown_transform():
    result = engine.apply_chain("x", [{"name": "missing"}], {})
    assert result.success is False
    assert result.error_code == "TRANSFORM_NOT_FOUND"
    assert result.value == "x"


def test_apply_chain_transform_failure_returns_before_value():
    result = engine.apply_chain("not-a-number", [{"name": "to_int"}], {})
    assert result.success is False
    assert result.error_code == "TRANSFORM_FAILED"
    assert result.value == "not-a-number"
    assert result.error_message


def test_apply_chain_empty_chain_is_identity():
    result = engine.apply_chain({"a": 1}, [], {})
    assert result.success is True
    assert result.value == {"a": 1}
    assert result.trace == []
