from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Any

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.database import Database

from app.config import get_settings
from app.database import create_client, ensure_indexes, ping_database

DEMO_PRODUCT_ID = ObjectId("0000000000000000000000d1")
DEMO_INVENTORY_ID = ObjectId("0000000000000000000000d2")


def seed_demo_inventory(db: Database) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    product = db["products"].find_one_and_update(
        {"_id": DEMO_PRODUCT_ID},
        {
            "$setOnInsert": {
                "brand_name": "YaSafe Demo Medicine",
                "generic_name": "Demo-only sample",
                "registration_no": "DEMO-ONLY-NOT-A-REAL-REGISTRATION",
                "manufacturer": "Demo data — no real manufacturer",
                "strength": None,
                "dosage_form": None,
                "data_origin": "demo",
                "created_at": now,
                "updated_at": now,
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    db["inventory_items"].find_one_and_update(
        {"_id": DEMO_INVENTORY_ID},
        {
            "$setOnInsert": {
                "product_id": product["_id"],
                "lot_number": "DEMO-ONLY-NOT-A-REAL-LOT",
                "quantity": 10,
                "expiry_date": datetime.combine(
                    date.today() + timedelta(days=365), datetime.min.time(), tzinfo=timezone.utc
                ),
                "is_demo": True,
                "created_at": now,
                "updated_at": now,
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return {
        "product_id": str(product["_id"]),
        "inventory_id": str(DEMO_INVENTORY_ID),
        "marked_as_demo": True,
        "official_notices_created": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Insert one clearly marked demo product and inventory lot."
    )
    parser.add_argument(
        "--confirm-demo-data",
        action="store_true",
        help="Confirm that demo-only inventory will be written to the configured database.",
    )
    args = parser.parse_args()
    if not args.confirm_demo_data:
        parser.error("Pass --confirm-demo-data to write demo-only records.")

    settings = get_settings()
    client = create_client(settings)
    try:
        db = client[settings.database_name]
        ping_database(db)
        ensure_indexes(db)
        result = seed_demo_inventory(db)
    finally:
        client.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
