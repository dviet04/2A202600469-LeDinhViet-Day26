from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal


class ValidationError(ValueError):
    """Raised when a request cannot be safely executed."""


FilterOp = Literal["eq", "ne", "lt", "lte", "gt", "gte", "like", "in"]
AggregateMetric = Literal["count", "avg", "sum", "min", "max"]


@dataclass(frozen=True)
class ColumnDef:
    name: str
    type: str | None
    notnull: bool
    default: Any
    pk: bool


def _dict_row_factory(cursor: sqlite3.Cursor, row: tuple[Any, ...]) -> dict[str, Any]:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


class SQLiteAdapter:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = _dict_row_factory
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [r["name"] for r in rows]

    def get_table_schema(self, table: str) -> list[ColumnDef]:
        self._validate_table(table)
        with self.connect() as conn:
            rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        # PRAGMA output: cid, name, type, notnull, dflt_value, pk
        return [
            ColumnDef(
                name=r["name"],
                type=r["type"],
                notnull=bool(r["notnull"]),
                default=r["dflt_value"],
                pk=bool(r["pk"]),
            )
            for r in rows
        ]

    def schema_snapshot(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {"tables": {}}
        for t in self.list_tables():
            snapshot["tables"][t] = {
                "columns": [c.__dict__ for c in self.get_table_schema(t)],
            }
        return snapshot

    def _validate_table(self, table: str) -> None:
        if not isinstance(table, str) or not table.strip():
            raise ValidationError("table must be a non-empty string")
        allowed = set(self.list_tables())
        if table not in allowed:
            raise ValidationError(f"unknown table: {table}")

    def _table_columns(self, table: str) -> set[str]:
        return {c.name for c in self.get_table_schema(table)}

    def _validate_columns(self, table: str, columns: Iterable[str]) -> None:
        allowed = self._table_columns(table)
        for c in columns:
            if c not in allowed:
                raise ValidationError(f"unknown column '{c}' for table '{table}'")

    def _build_where(
        self, table: str, filters: list[dict[str, Any]] | None
    ) -> tuple[str, list[Any]]:
        if not filters:
            return "", []

        if not isinstance(filters, list):
            raise ValidationError("filters must be a list of filter objects")

        clauses: list[str] = []
        params: list[Any] = []
        for f in filters:
            if not isinstance(f, dict):
                raise ValidationError("each filter must be an object")
            col = f.get("column")
            op = f.get("op")
            val = f.get("value")
            if not isinstance(col, str) or not col:
                raise ValidationError("filter.column must be a non-empty string")
            if op not in ("eq", "ne", "lt", "lte", "gt", "gte", "like", "in"):
                raise ValidationError(f"unsupported filter op: {op}")

            self._validate_columns(table, [col])

            if op == "eq":
                clauses.append(f"{col} = ?")
                params.append(val)
            elif op == "ne":
                clauses.append(f"{col} != ?")
                params.append(val)
            elif op == "lt":
                clauses.append(f"{col} < ?")
                params.append(val)
            elif op == "lte":
                clauses.append(f"{col} <= ?")
                params.append(val)
            elif op == "gt":
                clauses.append(f"{col} > ?")
                params.append(val)
            elif op == "gte":
                clauses.append(f"{col} >= ?")
                params.append(val)
            elif op == "like":
                if not isinstance(val, str):
                    raise ValidationError("LIKE filter value must be a string")
                clauses.append(f"{col} LIKE ?")
                params.append(val)
            elif op == "in":
                if not isinstance(val, list) or len(val) == 0:
                    raise ValidationError("IN filter value must be a non-empty list")
                placeholders = ",".join(["?"] * len(val))
                clauses.append(f"{col} IN ({placeholders})")
                params.extend(val)

        return "WHERE " + " AND ".join(clauses), params

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        self._validate_table(table)

        if columns is None:
            select_cols = "*"
        else:
            if not isinstance(columns, list) or any(not isinstance(c, str) for c in columns):
                raise ValidationError("columns must be a list of strings")
            if len(columns) == 0:
                raise ValidationError("columns must not be empty; omit to select all")
            self._validate_columns(table, columns)
            select_cols = ", ".join(columns)

        if not isinstance(limit, int) or limit <= 0 or limit > 200:
            raise ValidationError("limit must be an int between 1 and 200")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset must be a non-negative int")

        where_sql, params = self._build_where(table, filters)

        order_sql = ""
        if order_by is not None:
            if not isinstance(order_by, str) or not order_by:
                raise ValidationError("order_by must be a non-empty string")
            self._validate_columns(table, [order_by])
            order_sql = f"ORDER BY {order_by} {'DESC' if descending else 'ASC'}"

        sql = f"SELECT {select_cols} FROM {table} {where_sql} {order_sql} LIMIT ? OFFSET ?"
        params2 = [*params, limit, offset]

        with self.connect() as conn:
            rows = conn.execute(sql, params2).fetchall()
            # Separate count query for metadata
            count_sql = f"SELECT COUNT(*) AS cnt FROM {table} {where_sql}"
            total = conn.execute(count_sql, params).fetchone()["cnt"]

        has_more = (offset + limit) < int(total)
        next_offset = (offset + limit) if has_more else None
        return {
            "rows": rows,
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": has_more,
            "next_offset": next_offset,
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        self._validate_table(table)
        if not isinstance(values, dict) or len(values) == 0:
            raise ValidationError("values must be a non-empty object")

        cols = list(values.keys())
        if any((not isinstance(c, str)) or (not c) for c in cols):
            raise ValidationError("values keys must be non-empty strings")
        self._validate_columns(table, cols)

        placeholders = ", ".join(["?"] * len(cols))
        col_sql = ", ".join(cols)
        sql = f"INSERT INTO {table} ({col_sql}) VALUES ({placeholders})"
        params = [values[c] for c in cols]

        with self.connect() as conn:
            cur = conn.execute(sql, params)
            conn.commit()
            inserted = dict(values)
            if cur.lastrowid is not None:
                inserted.setdefault("id", cur.lastrowid)
        return {"inserted": inserted}

    def aggregate(
        self,
        table: str,
        metric: AggregateMetric,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        self._validate_table(table)
        if metric not in ("count", "avg", "sum", "min", "max"):
            raise ValidationError(f"unsupported metric: {metric}")

        where_sql, params = self._build_where(table, filters)

        if metric == "count":
            target = "*"
            if column is not None:
                if not isinstance(column, str) or not column:
                    raise ValidationError("column must be a non-empty string when provided")
                self._validate_columns(table, [column])
                target = column
            metric_sql = f"COUNT({target})"
        else:
            if not isinstance(column, str) or not column:
                raise ValidationError(f"metric '{metric}' requires 'column'")
            self._validate_columns(table, [column])
            metric_sql = f"{metric.upper()}({column})"

        group_sql = ""
        select_prefix = ""
        if group_by is not None:
            if not isinstance(group_by, str) or not group_by:
                raise ValidationError("group_by must be a non-empty string")
            self._validate_columns(table, [group_by])
            # Avoid reserved keywords like "GROUP" for aliases.
            select_prefix = f"{group_by} AS group_key, "
            group_sql = f"GROUP BY {group_by} ORDER BY {group_by} ASC"

        sql = f"SELECT {select_prefix}{metric_sql} AS value FROM {table} {where_sql} {group_sql}"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return {"rows": rows}

    def dump_schema_json(self) -> str:
        return json.dumps(self.schema_snapshot(), indent=2, ensure_ascii=False)
