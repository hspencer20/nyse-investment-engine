from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> dict[str, Any] | None:
    file_path = Path(path)
    if not file_path.exists():
        return None

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def write_text(path: str | Path, content: str) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def report_paths(report_dir: str, history_dir: str, report_type: str, generated_at: datetime) -> dict[str, Path]:
    slug = report_type.lower()
    timestamp = generated_at.strftime("%Y-%m-%d_%H%M")
    return {
        "latest_md": Path(report_dir) / "latest_report.md",
        "latest_json": Path(report_dir) / "latest_report.json",
        "typed_md": Path(report_dir) / f"latest_{slug}.md",
        "typed_json": Path(report_dir) / f"latest_{slug}.json",
        "history_json": Path(history_dir) / f"{timestamp}_{report_type}.json",
    }
