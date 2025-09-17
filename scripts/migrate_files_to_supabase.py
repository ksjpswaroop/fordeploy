"""
Upload existing local files from ./uploads and ./generated_docs to Supabase Storage.

- uploads -> bucket: settings.SUPABASE_STORAGE_BUCKET_UPLOADS, keys: recruiters/<rid>/candidates/<cid>/... (best-effort)
- generated_docs/run_<id>/* -> bucket: settings.SUPABASE_STORAGE_BUCKET_DOCS, keys: runs/<id>/<filename>

This script is idempotent (uses upsert). It does not delete any remote files.
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
import sys

# Ensure project root path import works even if executed from subdirectory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
import argparse

parser = argparse.ArgumentParser(description="Upload existing local files to Supabase Storage (idempotent).")
parser.add_argument("--dry-run", action="store_true", help="Scan and report counts without performing uploads")
parser.add_argument("--verbose", action="store_true", help="Print each file decision")
args, _ = parser.parse_known_args()

dry_run = args.dry_run
verbose = args.verbose

if not settings.supabase_storage_enabled and not dry_run:
    raise SystemExit("Supabase Storage not configured (set SUPABASE_URL and a key) or use --dry-run")

from app.services.supabase_storage import upload_bytes

ROOT = Path(os.getcwd())


def migrate_uploads() -> int:
    up_dir = ROOT / 'uploads'
    if not up_dir.exists():
        return 0
    count = 0
    for path in up_dir.rglob('*'):
        if path.is_dir():
            continue
        rel = path.relative_to(up_dir).as_posix()
        # Keep flat mapping under 'uploads/' prefix to avoid guessing candidate metadata
        key = rel
        try:
            with open(path, 'rb') as fh:
                data = fh.read()
            if dry_run:
                count += 1
                if verbose:
                    print(f"[DRY] uploads/{key}")
            else:
                if upload_bytes(settings.SUPABASE_STORAGE_BUCKET_UPLOADS, key, data, None, upsert=True):
                    count += 1
                    if verbose:
                        print(f"[OK] uploads/{key}")
        except Exception:
            pass
    return count


def migrate_generated_docs() -> int:
    gd_dir = ROOT / 'generated_docs'
    if not gd_dir.exists():
        return 0
    count = 0
    for path in gd_dir.rglob('*'):
        if path.is_dir():
            continue
        rel = path.relative_to(gd_dir).as_posix()
        # Map run_<id>/file -> runs/<id>/file
        parts = rel.split('/')
        if not parts:
            continue
        if parts[0].startswith('run_'):
            run_id = parts[0].split('_', 1)[1]
            key = 'runs/' + run_id + '/' + '/'.join(parts[1:])
        else:
            key = rel
        try:
            with open(path, 'rb') as fh:
                data = fh.read()
            # Guess content-type by extension
            ct = None
            if path.suffix == '.txt':
                ct = 'text/plain'
            elif path.suffix == '.docx':
                ct = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            if dry_run:
                count += 1
                if verbose:
                    print(f"[DRY] docs/{key}")
            else:
                if upload_bytes(settings.SUPABASE_STORAGE_BUCKET_DOCS, key, data, ct, upsert=True):
                    count += 1
                    if verbose:
                        print(f"[OK] docs/{key}")
        except Exception:
            pass
    return count


if __name__ == '__main__':
    up = migrate_uploads()
    docs = migrate_generated_docs()
    label_up = "scanned_uploads" if dry_run else "uploaded_uploads"
    label_docs = "scanned_generated_docs" if dry_run else "uploaded_generated_docs"
    print({label_up: up, label_docs: docs, "dry_run": dry_run})
