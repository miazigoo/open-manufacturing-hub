from app.variables.resolver import _stringify, build_runtime_scope, render_template


def test_build_runtime_scope_defaults():
    scope = build_runtime_scope(request_body=None)
    assert scope["request"]["body"] == {}
    assert scope["request"]["headers"] == {}
    assert scope["request"]["query"] == {}
    assert scope["request"]["raw_text"] is None
    assert scope["request"]["xml"] is None
    assert scope["variables"] == {}
    assert scope["steps"] == {}
    assert scope["context"] == {}


def test_build_runtime_scope_populates_and_flattens_variables():
    scope = build_runtime_scope(
        request_body={"id": 1},
        variables={"greeting": "hi", "steps": {"s1": {"ok": True}}},
        headers={"X-Test": "1"},
        query={"q": "v"},
        raw_text="raw",
        xml="<a/>",
        context={"trace": "t"},
    )
    assert scope["request"]["body"] == {"id": 1}
    assert scope["request"]["headers"] == {"X-Test": "1"}
    assert scope["request"]["query"] == {"q": "v"}
    assert scope["request"]["raw_text"] == "raw"
    assert scope["request"]["xml"] == "<a/>"
    assert scope["context"] == {"trace": "t"}
    assert scope["steps"] == {"s1": {"ok": True}}
    # variables are flattened into the top-level scope
    assert scope["greeting"] == "hi"


def test_render_template_full_placeholder_preserves_type():
    scope = build_runtime_scope(request_body={"n": 5, "flag": True, "obj": {"a": 1}})
    assert render_template("{{ request.body.n }}", scope) == 5
    assert render_template("{{ request.body.flag }}", scope) is True
    assert render_template("{{ request.body.obj }}", scope) == {"a": 1}


def test_render_template_partial_placeholder_stringifies():
    scope = build_runtime_scope(request_body={"n": 5})
    assert render_template("value=={{ request.body.n }}", scope) == "value==5"


def test_render_template_variable_shortcut():
    scope = build_runtime_scope(request_body={}, variables={"greeting": "hello"})
    assert render_template("{{ greeting }}", scope) == "hello"


def test_render_template_recurses_into_list_and_dict():
    scope = build_runtime_scope(request_body={"name": "widget"}, variables={"qty": 3})
    template = {"item": "{{ request.body.name }}", "tags": ["{{ qty }}", "static"]}
    rendered = render_template(template, scope)
    # full placeholders preserve type, so qty stays an int inside the list
    assert rendered == {"item": "widget", "tags": [3, "static"]}


def test_render_template_renders_dict_keys():
    scope = build_runtime_scope(request_body={"key": "dynamic"})
    rendered = render_template({"{{ request.body.key }}": "v"}, scope)
    assert rendered == {"dynamic": "v"}


def test_render_template_non_string_passthrough():
    scope = build_runtime_scope(request_body={})
    assert render_template(42, scope) == 42
    assert render_template(None, scope) is None


def test_stringify():
    assert _stringify(None) == ""
    assert _stringify("abc") == "abc"
    assert _stringify(5) == "5"
    assert _stringify({"a": 1}) == '{"a": 1}'
    assert _stringify([1, 2]) == "[1, 2]"
