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
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

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
        elif isinstance(value, dict):
            # We treat regex queries as always-matching for simplicity in tests
            # that don't need to verify search results precisely.
            if "$regex" in value:
                pass  # skip regex filtering in the fake — covered by real tests
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

    def create_index(self, *args, **kwargs):
        pass

    def insert_one(self, doc: dict) -> FakeInsertOneResult:
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self._docs.append(copy.deepcopy(doc))
        return FakeInsertOneResult(doc["_id"])

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
        self, query: dict, update: dict, return_document: bool = False
    ) -> Optional[dict]:
        for i, doc in enumerate(self._docs):
            if _matches_query(doc, query):
                if "$set" in update:
                    self._docs[i].update(update["$set"])
                return copy.deepcopy(self._docs[i]) if return_document else copy.deepcopy(doc)
        return None

    def count_documents(self, query: dict) -> int:
        return sum(1 for d in self._docs if _matches_query(d, query))

    def delete_one(self, query: dict) -> FakeDeleteResult:
        for i, doc in enumerate(self._docs):
            if _matches_query(doc, query):
                self._docs.pop(i)
                return FakeDeleteResult(1)
        return FakeDeleteResult(0)


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
        app = create_app()
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
    app = create_app()
    app.dependency_overrides[get_db] = lambda: fake_db
    return TestClient(app)
