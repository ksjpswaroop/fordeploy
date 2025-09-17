from __future__ import annotations

"""
Thin wrapper around Supabase Storage for optional backend file storage.

Usage:
    from app.services.supabase_storage import get_client, upload_bytes, get_public_url, create_signed_url, list_prefix

This module is a no-op when SUPABASE_URL and a key are not configured. Callers
should guard with `settings.supabase_storage_enabled` and degrade gracefully to
local filesystem.
"""

from typing import Optional, List, Dict, Any
from app.core.config import settings

_client = None  # cached client


def get_client():
    """Return a configured Supabase client or None when disabled."""
    global _client
    if not settings.supabase_storage_enabled:
        return None
    if _client is not None:
        return _client
    try:
        from supabase import create_client
        url = settings.SUPABASE_URL
        key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
        if not (url and key):
            return None
        _client = create_client(url, key)
        return _client
    except Exception:
        return None


def upload_bytes(bucket: str, path: str, data: bytes, content_type: Optional[str] = None, upsert: bool = True) -> bool:
    """Upload raw bytes to Supabase Storage. Returns True on success."""
    client = get_client()
    if not client:
        return False
    try:
        file_opts = {"upsert": upsert}
        if content_type:
            file_opts["contentType"] = content_type
        # The PyPI package supabase>=2 supports bytes directly.
        client.storage.from_(bucket).upload(path, data, file_options=file_opts)
        return True
    except Exception:
        return False


def get_public_url(bucket: str, path: str) -> Optional[str]:
    """Return public URL for object (works when bucket is public)."""
    client = get_client()
    if not client:
        return None
    try:
        res = client.storage.from_(bucket).get_public_url(path)
        # lib returns dict-like {'data': {'publicUrl': '...'}} in some versions
        if isinstance(res, dict):
            data = res.get("data") or {}
            return data.get("publicUrl") or res.get("publicURL") or None
        # Some versions return simple object with .data.public_url
        url = getattr(getattr(res, "data", None), "public_url", None)
        return url or None
    except Exception:
        return None


def create_signed_url(bucket: str, path: str, expires_in: int = 60 * 60) -> Optional[str]:
    """Return a time-limited signed URL for private buckets."""
    client = get_client()
    if not client:
        return None
    try:
        res = client.storage.from_(bucket).create_signed_url(path, expires_in)
        if isinstance(res, dict):
            data = res.get("data") or {}
            return data.get("signedUrl") or data.get("signedURL") or None
        url = getattr(getattr(res, "data", None), "signed_url", None)
        return url or None
    except Exception:
        return None


def list_prefix(bucket: str, prefix: str) -> List[Dict[str, Any]]:
    """List objects under a prefix. Returns [] on error."""
    client = get_client()
    if not client:
        return []
    try:
        # Note: path arg omits leading slash
        entries = client.storage.from_(bucket).list(path=prefix)
        # Normalize to a list of dicts with at least 'name' and 'id' if available
        if isinstance(entries, list):
            return entries
        return []
    except Exception:
        return []


__all__ = [
    "get_client",
    "upload_bytes",
    "get_public_url",
    "create_signed_url",
    "list_prefix",
]
