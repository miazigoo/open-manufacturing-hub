import pytest

from app.core.errors import BadRequestError
from app.external_errors import normalizers
from app.integration_master import parser as im_parser
from app.matchers import engine as matcher_engine
from app.packages_training import mock_onec_http
from app.xml_bridge.parser import XMLBridgeError, reject_unsafe_xml, secure_fromstring
from app.xml_tools import service as xml_tools_service

XXE = "<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><foo>&xxe;</foo>"
BILLION_LAUGHS = (
    "<!DOCTYPE lolz [<!ENTITY a \"AAAAAAAAAA\">"
    "<!ENTITY b \"&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;\">]><lolz>&b;</lolz>"
)


def test_reject_unsafe_xml_blocks_doctype_and_entity():
    for payload in (XXE, BILLION_LAUGHS):
        with pytest.raises(XMLBridgeError) as exc:
            reject_unsafe_xml(payload)
        assert exc.value.code == "XML_UNSAFE"


def test_secure_fromstring_parses_safe_xml():
    root = secure_fromstring("<root><child>value</child></root>")
    assert root.tag == "root"
    assert root[0].text == "value"


def test_matcher_xml_path_rejects_entity_payload():
    with pytest.raises(XMLBridgeError):
        matcher_engine._xml_path(XXE, "foo")


def test_integration_master_parser_rejects_entity_payload():
    with pytest.raises(BadRequestError):
        im_parser._parse_xml(BILLION_LAUGHS)


def test_external_error_xml_extractor_ignores_entity_payload():
    assert normalizers._extract_xml_message(XXE) is None


def test_training_mock_xml_reader_ignores_entity_payload():
    assert mock_onec_http._xml_text(XXE, "foo") is None


def test_xml_tools_pretty_does_not_expand_entities():
    assert xml_tools_service._pretty(BILLION_LAUGHS) == BILLION_LAUGHS
