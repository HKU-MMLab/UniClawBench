# API Changelog

## v3.4.2 — 2025-09-10

- **Fixed:** A race condition in `/v3/exports/start` that occasionally returned
  a 200 with an empty `export_id` when two requests landed in the same 50ms
  window from the same workspace.
- **Fixed:** `created_at` on the `Workspace` resource is now serialized as ISO
  8601 with timezone offset; previously it was a naive UTC string. Existing
  consumers that parse the field as ISO 8601 will continue to work.
- **Changed:** Default page size for `/v3/users` is now 50 (was 25). Pass
  `page_size` to override.

## v3.4.1 — 2025-08-28

- **Fixed:** Authentication errors on `/v3/exports` now return 401 instead of
  the previous (incorrect) 500.
- **Added:** `expand=workspace` parameter on the user list endpoint, returning
  the user's workspace memberships inline.

## v3.4.0 — 2025-08-15

- **Added:** New endpoint `POST /v3/audit-log/search` for compliance teams.
  Documented under the audit log section of the API guide.
- **Added:** Optional `idempotency_key` header on all POST endpoints. Server
  retains keys for 24 hours.
- **Deprecated:** `/v2/exports` is now deprecated. The 404 sunset window starts
  on 2026-02-15. Update integrations to `/v3/exports`.

## v3.3.4 — 2025-07-30

- **Fixed:** Pagination `next_page_token` was occasionally truncated when the
  underlying cursor exceeded 1024 bytes. Tokens are now URL-safe and unbounded
  in size.
- **Changed:** Webhook delivery now retries with exponential backoff up to
  6 attempts (was 4). Total delivery window remains 24 hours.
