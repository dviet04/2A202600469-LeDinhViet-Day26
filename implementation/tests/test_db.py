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


def test_insert_success(adapter: SQLiteAdapter) -> None:
    res = adapter.insert("students", {"name": "Test", "cohort": "C3", "score": 80.0})
    assert "inserted" in res
    assert res["inserted"]["name"] == "Test"
    assert res["inserted"]["cohort"] == "C3"
    assert res["inserted"]["score"] == 80.0
    assert "id" in res["inserted"]  # Should have auto-generated ID


def test_aggregate_count(adapter: SQLiteAdapter) -> None:
    res = adapter.aggregate("students", metric="count", column="id")
    assert "rows" in res
    assert len(res["rows"]) == 1
    assert res["rows"][0]["value"] >= 4  # At least 4 seeded students


def test_search_with_filters_and_columns(adapter: SQLiteAdapter) -> None:
    res = adapter.search(
        "students",
        columns=["name", "score"],
        filters=[{"column": "score", "op": "gte", "value": 85}],
        limit=10,
    )
    assert "rows" in res
    assert len(res["rows"]) >= 1
    # Check that only requested columns are returned
    for row in res["rows"]:
        assert "name" in row
        assert "score" in row
        assert row["score"] >= 85


def test_pagination_has_more(adapter: SQLiteAdapter) -> None:
    res = adapter.search("students", limit=2, offset=0)
    assert "has_more" in res
    assert "next_offset" in res
    # With 4+ students, has_more should be True with limit=2
    if res["total"] > 2:
        assert res["has_more"] is True
        assert res["next_offset"] == 2

