from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

# When launched as a file path (e.g. via MCP Inspector), Python may not treat this
# as a package, so `implementation.*` imports can fail depending on CWD.
if __package__ in (None, ""):
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

try:
    # Prefer package imports (`python -m implementation.mcp_server`)
    from .adapters import DatabaseAdapter, PostgresAdapter
    from .db import SQLiteAdapter, ValidationError
    from .init_db import create_database
except ImportError:  # allow `python implementation/mcp_server.py`
    from implementation.adapters import DatabaseAdapter, PostgresAdapter  # type: ignore
    from implementation.db import SQLiteAdapter, ValidationError  # type: ignore
    from implementation.init_db import create_database  # type: ignore


def _default_db_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "lab.sqlite3"


def _normalize_error(exc: Exception) -> Exception:
    if isinstance(exc, ValidationError):
        return ValueError(str(exc))
    return exc


def create_app(db_path: str | Path) -> FastMCP:
    db_path = str(db_path)
    adapter: DatabaseAdapter = SQLiteAdapter(db_path)

    mcp = FastMCP("SQLite Lab MCP Server")

    @mcp.tool(name="search")
    def search(
        table: str,
        filters: list[dict[str, Any]] | None = None,
        columns: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        try:
            return adapter.search(
                table=table,
                filters=filters,
                columns=columns,
                limit=limit,
                offset=offset,
                order_by=order_by,
                descending=descending,
            )
        except Exception as e:  # FastMCP will surface as tool error
            raise _normalize_error(e)

    @mcp.tool(name="insert")
    def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
        try:
            return adapter.insert(table=table, values=values)
        except Exception as e:
            raise _normalize_error(e)

    @mcp.tool(name="aggregate")
    def aggregate(
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        try:
            return adapter.aggregate(
                table=table,
                metric=metric,  # validated in adapter
                column=column,
                filters=filters,
                group_by=group_by,
            )
        except Exception as e:
            raise _normalize_error(e)

    @mcp.resource("schema://database")
    def database_schema() -> str:
        try:
            return adapter.dump_schema_json()
        except Exception as e:
            raise _normalize_error(e)

    @mcp.resource("schema://table/{table_name}")
    def table_schema(table_name: str) -> str:
        try:
            cols = adapter.get_table_schema(table_name)
            payload = {
                "table": table_name,
                "columns": [c.__dict__ for c in cols],
            }
            # keep ensure_ascii False for Vietnamese names if any in future
            import json

            return json.dumps(payload, indent=2, ensure_ascii=False)
        except Exception as e:
            raise _normalize_error(e)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite Lab FastMCP server")
    parser.add_argument(
        "--backend",
        choices=["sqlite", "postgres"],
        default=os.environ.get("SQLITE_LAB_BACKEND", "sqlite"),
        help="Database backend: sqlite (default) or postgres (bonus).",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get("SQLITE_LAB_DB", str(_default_db_path())),
        help="Path to the SQLite database file (or set SQLITE_LAB_DB).",
    )
    parser.add_argument(
        "--pg-dsn",
        default=os.environ.get("SQLITE_LAB_PG_DSN", ""),
        help="PostgreSQL DSN, required when --backend=postgres (or set SQLITE_LAB_PG_DSN).",
    )
    parser.add_argument(
        "--pg-schema",
        default=os.environ.get("SQLITE_LAB_PG_SCHEMA", "public"),
        help="PostgreSQL schema name (default: public).",
    )
    args = parser.parse_args()

    if args.backend == "sqlite":
        db_path = create_database(args.db)
        app = create_app(db_path)
    else:
        if not args.pg_dsn:
            raise SystemExit("--pg-dsn is required for --backend=postgres (or set SQLITE_LAB_PG_DSN)")
        adapter = PostgresAdapter(args.pg_dsn, schema=args.pg_schema)
        # create_app wires resources/tools around an adapter; for postgres we create here inline.
        mcp = FastMCP("SQLite Lab MCP Server (Postgres Backend)")

        @mcp.tool(name="search")
        def search(
            table: str,
            filters: list[dict[str, Any]] | None = None,
            columns: list[str] | None = None,
            limit: int = 20,
            offset: int = 0,
            order_by: str | None = None,
            descending: bool = False,
        ) -> dict[str, Any]:
            try:
                return adapter.search(
                    table=table,
                    filters=filters,
                    columns=columns,
                    limit=limit,
                    offset=offset,
                    order_by=order_by,
                    descending=descending,
                )
            except Exception as e:
                raise _normalize_error(e)

        @mcp.tool(name="insert")
        def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
            try:
                return adapter.insert(table=table, values=values)
            except Exception as e:
                raise _normalize_error(e)

        @mcp.tool(name="aggregate")
        def aggregate(
            table: str,
            metric: str,
            column: str | None = None,
            filters: list[dict[str, Any]] | None = None,
            group_by: str | None = None,
        ) -> dict[str, Any]:
            try:
                return adapter.aggregate(
                    table=table,
                    metric=metric,  # validated in adapter
                    column=column,
                    filters=filters,
                    group_by=group_by,
                )
            except Exception as e:
                raise _normalize_error(e)

        @mcp.resource("schema://database")
        def database_schema() -> str:
            try:
                return adapter.dump_schema_json()
            except Exception as e:
                raise _normalize_error(e)

        @mcp.resource("schema://table/{table_name}")
        def table_schema(table_name: str) -> str:
            try:
                cols = adapter.get_table_schema(table_name)
                payload = {"table": table_name, "columns": [c.__dict__ for c in cols]}
                import json

                return json.dumps(payload, indent=2, ensure_ascii=False)
            except Exception as e:
                raise _normalize_error(e)

        app = mcp
    app.run()


if __name__ == "__main__":
    main()
