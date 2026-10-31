from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.database import create_client, ensure_indexes, ping_database
from app.ingestion.import_service import import_records


def _read_records(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read valid JSON from {path}: {exc}") from exc
    records = value.get("records") if isinstance(value, dict) else value
    if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
        raise ValueError("Import file must be a JSON array or an object containing a records array.")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import manually verified Thai FDA Drug Alert records from JSON."
    )
    parser.add_argument("file", type=Path, help="Path to a reviewed JSON file")
    parser.add_argument(
        "--confirm-source-review",
        action="store_true",
        help="Confirm each record was checked against its official source URL.",
    )
    args = parser.parse_args()
    if not args.confirm_source_review:
        parser.error("Pass --confirm-source-review only after checking each source record.")

    records = _read_records(args.file)
    settings = get_settings()
    client = create_client(settings)
    try:
        db = client[settings.database_name]
        ping_database(db)
        ensure_indexes(db)
        result = import_records(db, records)
    finally:
        client.close()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
