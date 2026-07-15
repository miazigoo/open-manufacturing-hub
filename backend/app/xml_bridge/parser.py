from __future__ import annotations

from typing import Any
from xml.etree import ElementTree

from app.core.errors import BadRequestError

MAX_XML_SIZE_BYTES = 10 * 1024 * 1024


class XMLBridgeError(BadRequestError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_xml_size(xml_text: str, max_size_bytes: int = MAX_XML_SIZE_BYTES) -> int:
    size = len(xml_text.encode("utf-8"))
    if size > max_size_bytes:
        raise XMLBridgeError("XML_TOO_LARGE", f"XML payload is {size} bytes; limit is {max_size_bytes} bytes")
    return size


def reject_unsafe_xml(xml_text: str) -> None:
    """Block DOCTYPE/ENTITY declarations to prevent XXE and entity-expansion (billion laughs) attacks."""
    if "<!doctype" in xml_text.lower() or "<!entity" in xml_text.lower():
        raise XMLBridgeError("XML_UNSAFE", "DOCTYPE and ENTITY declarations are not allowed")


def secure_fromstring(xml_text: str, max_size_bytes: int = MAX_XML_SIZE_BYTES) -> ElementTree.Element:
    """Parse untrusted XML into an Element after size and entity-safety checks."""
    validate_xml_size(xml_text, max_size_bytes)
    reject_unsafe_xml(xml_text)
    return ElementTree.fromstring(xml_text)


def parse_xml_safe(xml_text: str, max_size_bytes: int = MAX_XML_SIZE_BYTES) -> dict[str, Any]:
    validate_xml_size(xml_text, max_size_bytes)
    reject_unsafe_xml(xml_text)
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise XMLBridgeError("XML_PARSE_FAILED", str(exc)) from exc
    return {root.tag: _element_to_dict(root)}


def build_xml_from_dict(value: dict[str, Any], root: str = "Document") -> str:
    element = ElementTree.Element(root)
    _append_dict(element, value)
    return ElementTree.tostring(element, encoding="unicode")


def _element_to_dict(element: ElementTree.Element) -> Any:
    children = list(element)
    result: dict[str, Any] = {}
    if element.attrib:
        result["@attributes"] = dict(element.attrib)
    text = (element.text or "").strip()
    if children:
        for child in children:
            child_value = _element_to_dict(child)
            existing = result.get(child.tag)
            if existing is None:
                result[child.tag] = child_value
            elif isinstance(existing, list):
                existing.append(child_value)
            else:
                result[child.tag] = [existing, child_value]
        if text:
            result["#text"] = text
        return result
    if result:
        if text:
            result["#text"] = text
        return result
    return text


def _append_dict(parent: ElementTree.Element, value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.startswith("@"):
                continue
            if isinstance(item, list):
                for child_item in item:
                    child = ElementTree.SubElement(parent, str(key))
                    _append_dict(child, child_item)
            else:
                child = ElementTree.SubElement(parent, str(key))
                _append_dict(child, item)
    elif value is not None:
        parent.text = str(value)
