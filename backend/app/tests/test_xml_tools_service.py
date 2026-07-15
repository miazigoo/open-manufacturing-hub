from app.xml_tools import service


def test_parse_valid_xml_reports_metadata_and_paths():
    result = service.parse("<Doc><Name>widget</Name></Doc>")
    assert result["valid"] is True
    assert result["error"] is None
    assert len(result["sha256"]) == 64
    assert result["size_bytes"] == len("<Doc><Name>widget</Name></Doc>".encode("utf-8"))
    assert result["parsed"] == {"Doc": {"Name": "widget"}}
    assert result["pretty_xml"]
    assert any("Name" in path for path in result["paths"])
    assert result["toolkit"]["success"] is True


def test_parse_invalid_xml_reports_error():
    result = service.parse("<Doc>")
    assert result["valid"] is False
    assert result["parsed"] is None
    assert result["pretty_xml"] is None
    assert result["paths"] == []
    assert result["error"]
    assert result["toolkit"]["success"] is False


def test_diff_detects_changes():
    result = service.diff("<A>1</A>", "<A>2</A>")
    assert result["same_hash"] is False
    assert result["forwarded_unchanged"] is False
    assert result["left_sha256"] != result["right_sha256"]
    assert "diff_text" in result and result["diff_text"]


def test_diff_identical_documents():
    result = service.diff("<A>1</A>", "<A>1</A>")
    assert result["same_hash"] is True
    assert result["forwarded_unchanged"] is True
    assert result["left_sha256"] == result["right_sha256"]
    assert result["diff_text"] == ""
