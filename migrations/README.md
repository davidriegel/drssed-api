# SQLSpec Migrations

This directory contains database migration files.

## File Format

Migration files use SQLFileLoader's named query syntax with versioned names:

```sql
-- name: migrate-20251011120000-up
CREATE TABLE example (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

-- name: migrate-20251011120000-down
DROP TABLE example;
```

## Naming Conventions

### File Names

Format: `{version}_{description}.sql`

- Version: Timestamp in YYYYMMDDHHmmss format (UTC)
- Description: Brief description using underscores
- Example: `20251011120000_create_users_table.sql`

### Query Names

- Upgrade: `migrate-{version}-up`
- Downgrade: `migrate-{version}-down`

## Version Format

Migrations use **timestamp-based versioning** (YYYYMMDDHHmmss):

- **Format**: 14-digit UTC timestamp
- **Example**: `20251011120000` (October 11, 2025 at 12:00:00 UTC)
- **Benefits**: Eliminates merge conflicts when multiple developers create migrations concurrently

### Creating Migrations

Use the CLI to generate timestamped migrations:

```bash
sqlspec create-migration "add user table"
# Creates: 20251011120000_add_user_table.sql
```

The timestamp is automatically generated in UTC timezone.

## Migration Execution

Migrations are applied in chronological order based on their timestamps.
The database tracks both version and execution order separately to handle
out-of-order migrations gracefully (e.g., from late-merging branches).

## Scheduled Events

`20260807143052_add_hard_delete_events.sql` purges soft-deleted clothing and
outfits after 7 days. Two things depend on that window:

- The MySQL event scheduler must be on (`--event-scheduler=ON`, set in both
  compose files). Without it the rows accumulate silently.
- The iOS client learns about deletions from `deleted` in the sync response, and
  a purged row no longer appears there. It falls back to a full, authoritative
  sync once its cursor is older than 7 days (`SyncManager.shouldPerformFullSync`),
  which is what keeps the two in step. Shortening the window here without
  shortening it there would leave clients with items the server has forgotten.
