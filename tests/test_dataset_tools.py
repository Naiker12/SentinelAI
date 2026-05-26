from __future__ import annotations

from datetime import datetime
from pathlib import Path

from tools.capture_dataset import build_capture_path, safe_name


def test_safe_name_normalizes_labels() -> None:
    assert safe_name("Cell Phone") == "cell_phone"
    assert safe_name(" objeto sospechoso! ") == "objeto_sospechoso"


def test_build_capture_path_uses_scenario_and_label() -> None:
    timestamp = datetime(2026, 5, 26, 12, 30, 1, 123456)

    path = build_capture_path(Path("dataset/raw"), "objeto_sospechoso", "knife", timestamp)

    assert path == Path("dataset/raw/objeto_sospechoso/knife/20260526_123001_123456_knife.jpg")
