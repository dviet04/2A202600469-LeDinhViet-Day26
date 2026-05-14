from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Protocol

from .db import SQLiteAdapter, ValidationError


AggregateMetric = Literal["count", "avg", "sum", "min", "max"]


class DatabaseAdapter(Protocol):
    def list_tables(self) -> list[str]: ...
    def get_table_schema(self, table: str) -> list[Any]: ...
    def dump_schema_json(self) -> str: ...
    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]: ...
    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]: ...
    def aggregate(
        self,
        table: str,
        metric: AggregateMetric,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class PostgresColumnDef:
    name: str
    type: str | None
    notnull: bool
    default: Any
    pk: bool


class PostgresAdapter:
    """
    Optional PostgreSQL backend.

    Requires `psycopg` (v3). Install with: `python -m pip install -r requirements-postgres.txt`
    """

    def __init__(self, dsn: str, schema: str = "public"):
        self.dsn = dsn
        self.schema = schema

        try:
            import psycopg  # noqa: F401
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "psycopg is required for PostgresAdapter. "
                "Install with: python -m pip install -r requirements-postgres.txt"
            ) from e

    def _connect(self):
        import psycopg

        return psycopg.connect(self.dsn)

    def list_tables(self) -> list[str]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
                (self.schema,),
            )
            return [r[0] for r in cur.fetchall()]

    def _validate_table(self, table: str) -> None:
        if not isinstance(table, str) or not table.strip():
            raise ValidationError("table must be a non-empty string")
        allowed = set(self.list_tables())
        if table not in allowed:
            raise ValidationError(f"unknown table: {table}")

    def get_table_schema(self, table: str) -> list[PostgresColumnDef]:
        self._validate_table(table)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                  c.column_name,
                  c.data_type,
                  (c.is_nullable = 'NO') AS notnull,
                  c.column_default,
                  COALESCE(tc.constraint_type = 'PRIMARY KEY', false) AS pk
                FROM information_schema.columns c
                LEFT JOIN information_schema.key_column_usage kcu
                  ON kcu.table_schema = c.table_schema
                 AND kcu.table_name = c.table_name
                 AND kcu.column_name = c.column_name
                LEFT JOIN information_schema.table_constraints tc
                  ON tc.table_schema = kcu.table_schema
                 AND tc.table_name = kcu.table_name
                 AND tc.constraint_name = kcu.constraint_name
                WHERE c.table_schema = %s
                  AND c.table_name = %s
                ORDER BY c.ordinal_position
                """,
                (self.schema, table),
            )
            rows = cur.fetchall()
        return [
            PostgresColumnDef(
                name=r[0],
                type=r[1],
                notnull=bool(r[2]),
                default=r[3],
                pk=bool(r[4]),
            )
            for r in rows
        ]

    def _table_columns(self, table: str) -> set[str]:
        return {c.name for c in self.get_table_schema(table)}

    def _validate_columns(self, table: str, columns: Iterable[str]) -> None:
        allowed = self._table_columns(table)
        for c in columns:
            if c not in allowed:
                raise ValidationError(f"unknown column '{c}' for table '{table}'")

    def dump_schema_json(self) -> str:
        snapshot: dict[str, Any] = {"tables": {}}
        for t in self.list_tables():
            snapshot["tables"][t] = {"columns": [c.__dict__ for c in self.get_table_schema(t)]}
        return json.dumps(snapshot, indent=2, ensure_ascii=False)

    def _build_where(
        self, table: str, filters: list[dict[str, Any]] | None
    ) -> tuple[Any, list[Any]]:
        from psycopg import sql

        if not filters:
            return sql.SQL(""), []
        if not isinstance(filters, list):
            raise ValidationError("filters must be a list of filter objects")

        clauses: list[Any] = []
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

            ident = sql.Identifier(col)
            if op == "eq":
                clauses.append(sql.SQL("{} = %s").format(ident))
                params.append(val)
            elif op == "ne":
                clauses.append(sql.SQL("{} != %s").format(ident))
                params.append(val)
            elif op == "lt":
                clauses.append(sql.SQL("{} < %s").format(ident))
                params.append(val)
            elif op == "lte":
                clauses.append(sql.SQL("{} <= %s").format(ident))
                params.append(val)
            elif op == "gt":
                clauses.append(sql.SQL("{} > %s").format(ident))
                params.append(val)
            elif op == "gte":
                clauses.append(sql.SQL("{} >= %s").format(ident))
                params.append(val)
            elif op == "like":
                if not isinstance(val, str):
                    raise ValidationError("LIKE filter value must be a string")
                clauses.append(sql.SQL("{} LIKE %s").format(ident))
                params.append(val)
            elif op == "in":
                if not isinstance(val, list) or len(val) == 0:
                    raise ValidationError("IN filter value must be a non-empty list")
                placeholders = sql.SQL(",").join([sql.Placeholder()] * len(val))
                clauses.append(sql.SQL("{} IN ({})").format(ident, placeholders))
                params.extend(val)

        where = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(clauses)
        return where, params

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
        from psycopg import sql

        self._validate_table(table)

        if columns is None:
            select_cols = sql.SQL("*")
        else:
            if not isinstance(columns, list) or any(not isinstance(c, str) for c in columns):
                raise ValidationError("columns must be a list of strings")
            if len(columns) == 0:
                raise ValidationError("columns must not be empty; omit to select all")
            self._validate_columns(table, columns)
            select_cols = sql.SQL(", ").join([sql.Identifier(c) for c in columns])

        if not isinstance(limit, int) or limit <= 0 or limit > 200:
            raise ValidationError("limit must be an int between 1 and 200")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("offset must be a non-negative int")

        where_sql, params = self._build_where(table, filters)

        order_sql = sql.SQL("")
        if order_by is not None:
            if not isinstance(order_by, str) or not order_by:
                raise ValidationError("order_by must be a non-empty string")
            self._validate_columns(table, [order_by])
            order_sql = sql.SQL(" ORDER BY {} {}").format(
                sql.Identifier(order_by),
                sql.SQL("DESC" if descending else "ASC"),
            )

        tbl = sql.Identifier(table)
        sch = sql.Identifier(self.schema)
        q = (
            sql.SQL("SELECT {} FROM {}.{}").format(select_cols, sch, tbl)
            + where_sql
            + order_sql
            + sql.SQL(" LIMIT %s OFFSET %s")
        )
        q_params = [*params, limit, offset]

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(q, q_params)
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]
            mapped = [dict(zip(cols, r)) for r in rows]

            c = sql.SQL("SELECT COUNT(*) FROM {}.{}").format(sch, tbl) + where_sql
            cur.execute(c, params)
            total = int(cur.fetchone()[0])

        has_more = (offset + limit) < total
        next_offset = (offset + limit) if has_more else None
        return {
            "rows": mapped,
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": has_more,
            "next_offset": next_offset,
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        from psycopg import sql

        self._validate_table(table)
        if not isinstance(values, dict) or len(values) == 0:
            raise ValidationError("values must be a non-empty object")

        cols = list(values.keys())
        if any((not isinstance(c, str)) or (not c) for c in cols):
            raise ValidationError("values keys must be non-empty strings")
        self._validate_columns(table, cols)

        sch = sql.Identifier(self.schema)
        tbl = sql.Identifier(table)
        col_sql = sql.SQL(", ").join([sql.Identifier(c) for c in cols])
        ph = sql.SQL(", ").join([sql.Placeholder()] * len(cols))

        q = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({}) RETURNING *").format(
            sch, tbl, col_sql, ph
        )
        params = [values[c] for c in cols]
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(q, params)
            row = cur.fetchone()
            out_cols = [d.name for d in cur.description]
            conn.commit()
        return {"inserted": dict(zip(out_cols, row))}

    def aggregate(
        self,
        table: str,
        metric: AggregateMetric,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        from psycopg import sql

        self._validate_table(table)
        if metric not in ("count", "avg", "sum", "min", "max"):
            raise ValidationError(f"unsupported metric: {metric}")

        where_sql, params = self._build_where(table, filters)

        if metric == "count":
            if column is None:
                metric_sql = sql.SQL("COUNT(*)")
            else:
                if not isinstance(column, str) or not column:
                    raise ValidationError("column must be a non-empty string when provided")
                self._validate_columns(table, [column])
                metric_sql = sql.SQL("COUNT({})").format(sql.Identifier(column))
        else:
            if not isinstance(column, str) or not column:
                raise ValidationError(f"metric '{metric}' requires 'column'")
            self._validate_columns(table, [column])
            metric_sql = sql.SQL("{}({})").format(sql.SQL(metric.upper()), sql.Identifier(column))

        select_prefix = sql.SQL("")
        group_sql = sql.SQL("")
        if group_by is not None:
            if not isinstance(group_by, str) or not group_by:
                raise ValidationError("group_by must be a non-empty string")
            self._validate_columns(table, [group_by])
            select_prefix = sql.SQL("{} AS group_key, ").format(sql.Identifier(group_by))
            group_sql = sql.SQL(" GROUP BY {} ORDER BY {} ASC").format(
                sql.Identifier(group_by), sql.Identifier(group_by)
            )

        sch = sql.Identifier(self.schema)
        tbl = sql.Identifier(table)
        q = (
            sql.SQL("SELECT ").join([sql.SQL("")])  # no-op join for type
        )
        q = sql.SQL("SELECT ") + select_prefix + metric_sql + sql.SQL(" AS value FROM {}.{}").format(
            sch, tbl
        )
        q = q + where_sql + group_sql

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(q, params)
            rows = cur.fetchall()
            cols = [d.name for d in cur.description]
            mapped = [dict(zip(cols, r)) for r in rows]
        return {"rows": mapped}


def create_sqlite_adapter(db_path: str) -> SQLiteAdapter:
    return SQLiteAdapter(db_path)

