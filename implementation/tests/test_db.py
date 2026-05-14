from __future__ import annotations

from pathlib import Path

import pytest

from implementation.db import SQLiteAdapter, ValidationError
from implementation.init_db import create_database


@pytest.fixture()
def adapter(tmp_path: Path) -> SQLiteAdapter:
    db_path = tmp_path / "lab.sqlite3"
    create_database(db_path)
    return SQLiteAdapter(db_path)


def test_list_tables(adapter: SQLiteAdapter) -> None:
    tables = adapter.list_tables()
    assert set(tables) >= {"students", "courses", "enrollments"}


def test_reject_unknown_table(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ValidationError):
        adapter.search("missing_table")


def test_reject_unknown_column(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ValidationError):
        adapter.search("students", columns=["does_not_exist"])


def test_reject_unsupported_op(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ValidationError):
        adapter.search("students", filters=[{"column": "cohort", "op": "regex", "value": "A1"}])


def test_search_order_limit(adapter: SQLiteAdapter) -> None:
    res = adapter.search("students", order_by="score", descending=True, limit=2, offset=0)
    assert res["limit"] == 2
    assert res["offset"] == 0
    assert res["total"] >= 4
    assert len(res["rows"]) == 2


def test_insert_requires_values(adapter: SQLiteAdapter) -> None:
    with pytest.raises(ValidationError):
        adapter.insert("students", {})


def test_aggregate_avg(adapter: SQLiteAdapter) -> None:
    res = adapter.aggregate("students", metric="avg", column="score", group_by="cohort")
    assert "rows" in res
    assert len(res["rows"]) >= 1

