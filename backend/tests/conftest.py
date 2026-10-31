"""
Shared pytest fixtures.

FakeDB simulates the subset of PyMongo behaviour used by the app so tests run
without a real MongoDB Atlas connection.

Design:
- FakeCollection stores documents in a plain Python list.
- Supports the operations our service layer calls: insert_one, find, find_one,
  find_one_and_update, count_documents, delete_one, create_index.
- ObjectId generation uses bson.ObjectId so the rest of the code doesn't need
  to know it's faking.

This is intentionally minimal — it covers what Phase 1-2 needs. Later phases
will extend it as required.
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError
from pymongo import UpdateOne

from app.dependencies import get_db
from app.main import create_app


# ---------------------------------------------------------------------------
# Fake MongoDB layer
# ---------------------------------------------------------------------------


class FakeInsertOneResult:
    def __init__(self, inserted_id: ObjectId):
        self.inserted_id = inserted_id


class FakeDeleteResult:
    def __init__(self, deleted_count: int):
        self.deleted_count = deleted_count


def _matches_query(doc: dict, query: dict) -> bool:
    """
    Very small subset of MongoDB query language for testing:
      - exact field match       {"field": value}
      - $or                     {"$or": [q1, q2, ...]}
      - $regex (ignored)        {"field": {"$regex": "...", "$options": "i"}}
      - ObjectId field match
    """
    for key, value in query.items():
        if key == "$or":
            if not any(_matches_query(doc, sub) for sub in value):
                return False
        elif key == "$and":
            if not all(_matches_query(doc, sub) for sub in value):
                return False
        elif "." in key:
            found = doc
            for part in key.split("."):
                found = found.get(part) if isinstance(found, dict) else None
            if isinstance(value, dict) and "$regex" in value:
                options = re.IGNORECASE if value.get("$options") == "i" else 0
                candidates = found if isinstance(found, list) else [found]
                if not any(re.search(value["$regex"], str(candidate or ""), options) for candidate in candidates):
                    return False
            elif found != value:
                return False
        elif isinstance(value, dict):
            if "$regex" in value:
                options = re.IGNORECASE if value.get("$options") == "i" else 0
                candidates = doc.get(key) if isinstance(doc.get(key), list) else [doc.get(key)]
                if not any(re.search(value["$regex"], str(candidate or ""), options) for candidate in candidates):
                    return False
            elif "$in" in value:
                if doc.get(key) not in value["$in"]:
                    return False
            elif "$gte" in value or "$lte" in value:
                candidate = doc.get(key)
                if candidate is None:
                    return False
                lower = value.get("$gte")
                upper = value.get("$lte")
                if lower is not None and candidate < lower:
                    return False
                if upper is not None and candidate > upper:
                    return False
            else:
                return False
        else:
            if doc.get(key) != value:
                return False
    return True


class FakeCursor:
    def __init__(self, docs: list[dict]):
        self._docs = list(docs)
        self._skip_n = 0
        self._limit_n = 0

    def sort(self, *args, **kwargs) -> "FakeCursor":
        if args:
            sort_spec = args[0]
            if isinstance(sort_spec, str):
                sort_spec = [(sort_spec, args[1] if len(args) > 1 else 1)]
            for key, direction in reversed(sort_spec):
                self._docs.sort(
                    key=lambda doc: (doc.get(key) is not None, doc.get(key)),
                    reverse=direction < 0,
                )
        return self

    def skip(self, n: int) -> "FakeCursor":
        self._skip_n = n
        return self

    def limit(self, n: int) -> "FakeCursor":
        self._limit_n = n
        return self

    def __iter__(self):
        docs = self._docs[self._skip_n :]
        if self._limit_n:
            docs = docs[: self._limit_n]
        return iter(docs)


class FakeCollection:
    def __init__(self):
        self._docs: list[dict] = []
        self.indexes: list[tuple] = []

    def create_index(self, *args, **kwargs):
        self.indexes.append((args, kwargs))

    def insert_one(self, doc: dict) -> FakeInsertOneResult:
        if "_id" in doc and any(existing.get("_id") == doc["_id"] for existing in self._docs):
            raise DuplicateKeyError("duplicate key _id")
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self._docs.append(copy.deepcopy(doc))
        return FakeInsertOneResult(doc["_id"])

    def bulk_write(self, requests: list, ordered: bool = True):
        for request in requests:
            if not isinstance(request, UpdateOne):
                raise TypeError(f"Unsupported bulk operation: {type(request).__name__}")
            self.find_one_and_update(
                request._filter,
                request._doc,
                upsert=request._upsert,
            )

    def find(self, query: dict = None, projection: dict = None) -> FakeCursor:
        query = query or {}
        matched = [copy.deepcopy(d) for d in self._docs if _matches_query(d, query)]
        return FakeCursor(matched)

    def find_one(self, query: dict, projection: dict = None) -> Optional[dict]:
        query = query or {}
        for doc in self._docs:
            if _matches_query(doc, query):
                return copy.deepcopy(doc)
        return None

    def find_one_and_update(
        self, query: dict, update: dict, return_document: bool = False, upsert: bool = False, **kwargs
    ) -> Optional[dict]:
        for i, doc in enumerate(self._docs):
            if _matches_query(doc, query):
                previous = copy.deepcopy(doc)
                if "$set" in update:
                    self._docs[i].update(update["$set"])
                return copy.deepcopy(self._docs[i]) if return_document else previous
        if upsert:
            new_doc = {**query, **update.get("$setOnInsert", {}), **update.get("$set", {})}
            new_doc.pop("$setOnInsert", None)
            new_doc.pop("$set", None)
            if "_id" not in new_doc:
                new_doc["_id"] = ObjectId()
            self._docs.append(copy.deepcopy(new_doc))
            return copy.deepcopy(new_doc)
        return None

    def count_documents(self, query: dict) -> int:
        return sum(1 for d in self._docs if _matches_query(d, query))

    def delete_one(self, query: dict) -> FakeDeleteResult:
        for i, doc in enumerate(self._docs):
            if _matches_query(doc, query):
                self._docs.pop(i)
                return FakeDeleteResult(1)
        return FakeDeleteResult(0)

    def delete_many(self, query: dict) -> FakeDeleteResult:
        before = len(self._docs)
        self._docs = [doc for doc in self._docs if not _matches_query(doc, query)]
        return FakeDeleteResult(before - len(self._docs))


class FakeAdmin:
    def __init__(self, fail: bool = False):
        self._fail = fail

    def command(self, name: str) -> dict:
        if self._fail:
            raise ConnectionError("simulated MongoDB outage")
        return {"ok": 1}


class FakeClient:
    def __init__(self, fail: bool = False):
        self.admin = FakeAdmin(fail)


class FakeDB:
    """
    In-memory database.  Each collection is a FakeCollection stored by name.
    A fresh FakeDB() starts empty; tests populate it as needed.
    """

    def __init__(self, fail: bool = False):
        self.client = FakeClient(fail)
        self._collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        if name not in self._collections:
            self._collections[name] = FakeCollection()
        return self._collections[name]


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_db() -> FakeDB:
    """Return a fresh empty FakeDB for each test."""
    return FakeDB()


@pytest.fixture
def make_client(fake_db):
    """
    Factory fixture: returns a TestClient whose get_db dependency is wired to
    the shared fake_db, so tests can pre-populate collections and then call
    the API.
    """
    def _make(db_fails: bool = False) -> TestClient:
        db = FakeDB(fail=db_fails) if db_fails else fake_db
        app = create_app(manage_database=False)
        app.dependency_overrides[get_db] = lambda: db
        return TestClient(app)

    return _make


@pytest.fixture
def client(fake_db) -> TestClient:
    """
    Convenience fixture: a ready-to-use TestClient backed by fake_db.
    Use this for tests that only need to call endpoints.
    Use make_client when you also need to inspect or pre-populate fake_db.
    """
    app = create_app(manage_database=False)
    app.dependency_overrides[get_db] = lambda: fake_db
    return TestClient(app)
