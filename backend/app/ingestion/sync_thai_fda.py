from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.config import get_settings
from app.database import create_client, ensure_indexes, ping_database
from app.services.sync_service import (
    begin_sync,
    execute_sync,
    record_skipped_sync,
    scheduled_sync_due,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize notices from the publicly referenced Thai FDA listing."
    )
    parser.add_argument(
        "--trigger",
        choices=("MANUAL", "SCHEDULED"),
        default="MANUAL",
        help="Label this run for synchronization history.",
    )
    parser.add_argument(
        "--confirm-source-sync",
        action="store_true",
        help="Confirm that this command may write fetched records and run history to MongoDB.",
    )
    args = parser.parse_args()
    settings = get_settings()
    if not settings.fda_sync_enabled:
        parser.error("Set FDA_SYNC_ENABLED=true before running synchronization.")
    if not args.confirm_source_sync:
        parser.error("Pass --confirm-source-sync to confirm persistent synchronization.")

    client = create_client(settings)
    try:
        db = client[settings.database_name]
        ping_database(db)
        ensure_indexes(db)
        if args.trigger == "SCHEDULED" and not scheduled_sync_due(
            db, settings.fda_sync_interval_hours
        ):
            result = record_skipped_sync(db)
            print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
            return 0
        run_id, acquired = begin_sync(db, args.trigger)
        if not acquired:
            print(json.dumps({
                "run_id": run_id,
                "status": "FAILED",
                "error_summary": "Another FDA synchronization is already running.",
            }))
            return 2
        result: dict[str, Any] = execute_sync(db, run_id, settings)
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        return 1 if result["status"] == "FAILED" else 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
