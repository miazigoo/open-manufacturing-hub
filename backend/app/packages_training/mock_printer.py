from __future__ import annotations

from typing import Any


def print_label(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    printer = str(payload.get("printer") or payload.get("printer_id") or payload.get("printer_name") or "TRAINING-PRINTER-01")
    if printer == "TRAINING-OFFLINE":
        return 503, {
            "success": False,
            "error": "TRAINING_PRINTER_OFFLINE",
            "error_code": "PRINTER_OFFLINE",
            "error_message": "Training printer is offline",
            "message": "Training printer is offline by design.",
            "hint": "Switch printer to TRAINING-PRINTER-01 or inspect retry/DLQ behavior.",
        }
    return 200, {
        "success": True,
        "printer": printer,
        "job_id": "TRAIN-PRINT-001",
        "status": "sent",
    }
