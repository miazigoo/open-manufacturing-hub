import pytest

from app.xml_bridge.parser import (
    MAX_XML_SIZE_BYTES,
    XMLBridgeError,
    build_xml_from_dict,
    parse_xml_safe,
    validate_xml_size,
)


def test_validate_xml_size_returns_byte_length():
    assert validate_xml_size("abc") == 3
    assert validate_xml_size("é") == 2  # 2 bytes in UTF-8


def test_validate_xml_size_rejects_oversized_payload():
    with pytest.raises(XMLBridgeError) as excinfo:
        validate_xml_size("abcd", max_size_bytes=2)
    assert excinfo.value.code == "XML_TOO_LARGE"


def test_parse_xml_safe_simple_element():
    assert parse_xml_safe("<Doc><Name>widget</Name></Doc>") == {"Doc": {"Name": "widget"}}


def test_parse_xml_safe_repeated_children_become_list():
    parsed = parse_xml_safe("<Doc><Item>1</Item><Item>2</Item></Doc>")
    assert parsed == {"Doc": {"Item": ["1", "2"]}}


def test_parse_xml_safe_attributes_and_text():
    parsed = parse_xml_safe('<Doc><Node id="7">text</Node></Doc>')
    assert parsed == {"Doc": {"Node": {"@attributes": {"id": "7"}, "#text": "text"}}}


def test_parse_xml_safe_mixed_children_and_text():
    parsed = parse_xml_safe("<Doc>hello<Child>c</Child></Doc>")
    assert parsed == {"Doc": {"Child": "c", "#text": "hello"}}


def test_parse_xml_safe_empty_element_returns_empty_string():
    assert parse_xml_safe("<Doc></Doc>") == {"Doc": ""}


def test_parse_xml_safe_rejects_doctype():
    with pytest.raises(XMLBridgeError) as excinfo:
        parse_xml_safe("<!DOCTYPE foo><Doc/>")
    assert excinfo.value.code == "XML_UNSAFE"


def test_parse_xml_safe_rejects_entity_declaration():
    with pytest.raises(XMLBridgeError) as excinfo:
        parse_xml_safe("<!ENTITY x 'y'><Doc/>")
    assert excinfo.value.code == "XML_UNSAFE"


def test_parse_xml_safe_invalid_xml_raises_parse_error():
    with pytest.raises(XMLBridgeError) as excinfo:
        parse_xml_safe("<Doc>")
    assert excinfo.value.code == "XML_PARSE_FAILED"


def test_build_xml_from_dict_roundtrips_nested_and_lists():
    xml = build_xml_from_dict({"Name": "widget", "Meta": {"C": "2"}, "Items": [{"i": "a"}, {"i": "b"}]}, root="Order")
    assert xml == "<Order><Name>widget</Name><Meta><C>2</C></Meta><Items><i>a</i></Items><Items><i>b</i></Items></Order>"


def test_build_xml_from_dict_default_root_and_skips_attribute_keys():
    xml = build_xml_from_dict({"@ignored": "x", "Kept": "y"})
    assert xml == "<Document><Kept>y</Kept></Document>"


def test_max_size_constant_is_ten_megabytes():
    assert MAX_XML_SIZE_BYTES == 10 * 1024 * 1024
