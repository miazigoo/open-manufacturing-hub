"""Minimal GS1 parser for Chestny Znak marking codes.

Expected shape: 01<14-digit GTIN>21<serial><GS>...(crypto tail, e.g. AI 91/92/93).
The parser is fault tolerant: when a code does not match the expected shape the
optional fields stay empty and routing rules simply do not match them.
"""
from __future__ import annotations

GS = "\x1d"


def parse_code(code: str) -> dict[str, str]:
    result = {"code": code, "gtin": "", "serial": "", "ai93": ""}
    if not code or not code.startswith("01") or len(code) < 16:
        return result
    result["gtin"] = code[2:16]
    rest = code[16:]
    if not rest.startswith("21"):
        return result
    serial, separator, tail = rest[2:].partition(GS)
    result["serial"] = serial
    if separator and tail.startswith("93"):
        result["ai93"] = tail[2:].split(GS)[0]
    return result
