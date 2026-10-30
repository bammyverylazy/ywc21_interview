"""MongoDB connection and index setup.

LotShield uses synchronous PyMongo with synchronous route handlers. Do not mix in
the async PyMongo API without a clear reason.
"""

import logging

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from app.config import Settings

logger = logging.getLogger("lotshield.database")

# (collection, field, direction) - matches the recommended indexes in README 6.8.
# No unique indexes yet: duplicate-handling rules are not confirmed.
INDEXES: list[tuple[str, str, int]] = [
    ("products", "registration_no", ASCENDING),
    ("products", "brand_name", ASCENDING),
    ("inventory_items", "product_id", ASCENDING),
    ("inventory_items", "lot_number", ASCENDING),
    ("safety_notices", "registration_no", ASCENDING),
    ("safety_notices", "published_at", DESCENDING),
    ("safety_notices", "source_url", ASCENDING),
    ("matches", "inventory_id", ASCENDING),
    ("matches", "notice_id", ASCENDING),
    ("matches", "match_status", ASCENDING),
    ("action_logs", "match_id", ASCENDING),
]


def create_client(settings: Settings) -> MongoClient:
    # MongoClient connects lazily; a short selection timeout keeps failures fast.
    return MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)


def ping_database(db: Database) -> None:
    """Raise if the database cannot be reached."""
    db.client.admin.command("ping")


def ensure_indexes(db: Database) -> None:
    """Create the recommended indexes. Safe to call repeatedly (idempotent)."""
    for collection, field, direction in INDEXES:
        db[collection].create_index([(field, direction)])
