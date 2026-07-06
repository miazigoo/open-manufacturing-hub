from __future__ import annotations

import json
import re
from typing import Any
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from app.variables.paths import PathResolutionError, resolve_path


class XmlTemplateError(ValueError):
    pass


def render_xml_template(template: str, variables: dict[str, Any], *, validate_xml: bool = True) -> str:
    missing: list[str] = []

    def replace(match: re.Match[str]) -> str:
        expression = match.group(1).strip()
        try:
            value = resolve_path(variables, expression)
        except PathResolutionError:
            missing.append(expression)
            return ""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        if value is None:
            value = ""
        return escape(str(value), {'"': "&quot;", "'": "&apos;"})

    rendered = re.sub(r"{{\s*([^{}]+?)\s*}}", replace, template)
    if missing:
        raise XmlTemplateError(f"Missing XML template variables: {', '.join(missing)}")
    if validate_xml:
        try:
            ElementTree.fromstring(rendered)
        except ElementTree.ParseError as exc:
            raise XmlTemplateError(f"Rendered XML is not valid: {exc}") from exc
    return rendered

