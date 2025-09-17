# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Notifications API under `/api/v1/notifications` with list, read, dismiss, unread-count, mark-all-read, and delete.
- PaginatedResponse standardization for notifications and bench lists.
- Database indexes on `notifications` for `is_read`, `is_dismissed`, `created_at`, and composite `(user_id, created_at)`.
- CI improvements: Python matrix (3.10–3.12), pip caching, ruff/black/mypy enforcement, coverage gate 85%.
- Tests for notifications pagination, dismissed filter, and RBAC; updated bench tests for pagination.

### Changed
- Deprecated `/api/v1/common/notifications` endpoints; now return 410 Gone.

### Notes
- Clients should migrate to `/api/v1/notifications` and adapt to the paginated response shape.
