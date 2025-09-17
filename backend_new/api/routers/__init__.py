"""Lightweight routers package init.

We intentionally avoid importing every router eagerly because some legacy
routers reference schemas that may be in flux. Each submodule can still be
imported directly (e.g. `from app.api.routers import health`).
"""

__all__ = [
	'health', 'pipeline', 'jobflow', 'public', 'recruiter_candidates'
]