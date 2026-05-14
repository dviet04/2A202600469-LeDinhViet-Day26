from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

try:
    from .db import SQLiteAdapter
    from .init_db import create_database
except ImportError:  # allow `python implementation/verify_server.py`
    from implementation.db import SQLiteAdapter  # type: ignore
    from implementation.init_db import create_database  # type: ignore


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless verification for sqlite-lab")
    parser.add_argument(
        "--db",
        default=str(Path(__file__).resolve().parent / "data" / "lab.sqlite3"),
        help="Path to SQLite DB (created if missing).",
    )
    args = parser.parse_args()

    db_path = create_database(args.db)
    adapter = SQLiteAdapter(db_path)

    print("== Tables ==")
    print(adapter.list_tables())

    print("\n== schema://database (preview) ==")
    schema_json = adapter.dump_schema_json()
    print(schema_json[:400] + ("..." if len(schema_json) > 400 else ""))

    print("\n== search students cohort=A1 (top 2 by score) ==")
    res = adapter.search(
        table="students",
        filters=[{"column": "cohort", "op": "eq", "value": "A1"}],
        order_by="score",
        descending=True,
        limit=2,
        offset=0,
    )
    print(res)

    print("\n== insert student ==")
    ins = adapter.insert(table="students", values={"name": "Eva", "cohort": "A1", "score": 89.0})
    print(ins)

    print("\n== aggregate avg(score) by cohort ==")
    agg = adapter.aggregate(table="students", metric="avg", column="score", group_by="cohort")
    print(agg)

    print("\n== Next: MCP Inspector ==")
    print("Run (replace python path if needed):")
    print(
        "  npx -y @modelcontextprotocol/inspector python -m implementation.mcp_server"
    )


if __name__ == "__main__":
    main()
