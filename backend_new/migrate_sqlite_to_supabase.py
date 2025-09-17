#!/usr/bin/env python3
"""
One-off migration: copy data from local SQLite to Supabase Postgres using SQLAlchemy models.
Usage:
  source .venv/bin/activate
  export SUPABASE_POSTGRES_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/postgres?sslmode=require
  python scripts/migrate_sqlite_to_supabase.py

Notes:
- Orders tables by foreign-key dependencies using SQLAlchemy MetaData.
- Skips duplicates on PK conflicts (best-effort upsert by primary key).
- Copies in batches for large tables.
"""
from __future__ import annotations
import os
import sys
import argparse
from typing import Iterable
from sqlalchemy import create_engine, inspect, Table
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

# Force Settings to prefer SQLite for source and Supabase for target
"""Migration script from local SQLite to a target (Supabase Postgres or other SQLAlchemy URL).

Enhancements added:
 - Adds CLI arguments so you can run without exporting env vars:
     python scripts/migrate_sqlite_to_supabase.py --target postgresql+psycopg2://... --source recruitment_mvp.db
 - Falls back to --target if SUPABASE_POSTGRES_URL / DATABASE_URL not set.
 - Allows using an alternative target (e.g., temporary sqlite:///./supabase_test.db) for dry-runs.
 - Adds a sys.path injection so running from subdirectories still locates the 'app' package.
"""

# Ensure project root is on sys.path (handles execution from nested CWDs)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.core.config import Settings  # noqa: E402
from app.models.base import Base  # noqa: E402
import app.models  # noqa: F401,E402 - register all models

parser = argparse.ArgumentParser(description="Copy data from local SQLite to Supabase (or any target) using SQLAlchemy models.")
parser.add_argument("--source", default=os.getenv("SQLITE_DATABASE_URL", "recruitment_mvp.db"), help="Source SQLite file path or full SQLAlchemy URL (default: recruitment_mvp.db)")
parser.add_argument("--target", default=os.getenv("SUPABASE_POSTGRES_URL") or os.getenv("DATABASE_URL"), help="Target SQLAlchemy DB URL (Supabase Postgres). Overrides env if provided.")
parser.add_argument("--batch-size", type=int, default=500, help="Insert batch size (default 500)")
parser.add_argument("--skip-empty", action="store_true", help="Skip printing tables that are empty (quiet mode for empties)")
args = parser.parse_args()

SQLITE_URL = args.source if "://" in args.source else f"sqlite:///./{args.source}"
SUPABASE_URL = args.target
if not SUPABASE_URL:
    print("[ERROR] Missing target DB URL. Provide --target or export SUPABASE_POSTGRES_URL / DATABASE_URL.")
    print("Example (Supabase): export SUPABASE_POSTGRES_URL=postgresql+psycopg2://USER:PASS@HOST:5432/postgres?sslmode=require")
    print("Example (Dry run to another local sqlite file): python scripts/migrate_sqlite_to_supabase.py --target sqlite:///./supabase_mirror.db")
    sys.exit(1)

## Normalize scheme for psycopg2 (only for Postgres URLs)
if SUPABASE_URL.startswith("postgres://"):
    SUPABASE_URL = SUPABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
if SUPABASE_URL.startswith("postgresql://") and not SUPABASE_URL.startswith("postgresql+psycopg2://"):
    SUPABASE_URL = SUPABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

src_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
dst_engine = create_engine(SUPABASE_URL, pool_pre_ping=True)

# Ensure target tables exist (run Alembic separately in CI/CD for real usage)
Base.metadata.create_all(bind=dst_engine)

META = Base.metadata

def topologically_sorted_tables(meta) -> list[Table]:
    # Alembic has a helper but we can do a simple Kahn topo sort via dependencies
    tables = list(meta.sorted_tables)
    return tables

def chunk(iterable: Iterable, size: int):
    buf = []
    for x in iterable:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

copied_total = 0
with src_engine.connect() as src_conn, dst_engine.begin() as dst_conn:
    insp = inspect(src_conn)
    for table in topologically_sorted_tables(META):
        name = table.name
        if name.startswith("alembic_"):
            continue
        print(f"\n== Table {name} ==")
        # Pull rows from source
        try:
            src_rows = src_conn.execute(table.select()).fetchall()
        except Exception as e:
            print(f"Skip {name}: cannot read source ({e})")
            continue
        if not src_rows:
            if not args.skip_empty:
                print("Empty; skipping")
            continue
        inserted = 0
        for batch in chunk((dict(r._mapping) for r in src_rows), args.batch_size):
            try:
                if dst_engine.dialect.name == 'postgresql':
                    # Use dialect-specific upsert that ignores conflicts
                    stmt = pg_insert(table).on_conflict_do_nothing()
                    dst_conn.execute(stmt, batch)
                else:
                    dst_conn.execute(table.insert(), batch)
                inserted += len(batch)
            except Exception as e:
                # Fallback to per-row inserts to skip conflicting/invalid rows
                for row in batch:
                    try:
                        if dst_engine.dialect.name == 'postgresql':
                            stmt = pg_insert(table).on_conflict_do_nothing()
                            dst_conn.execute(stmt, row)
                        else:
                            dst_conn.execute(table.insert(), row)
                        inserted += 1
                    except Exception:
                        pass
        print(f"Copied {inserted} rows")
        copied_total += inserted
print(f"\nMigration complete. Total copied rows: {copied_total}")
