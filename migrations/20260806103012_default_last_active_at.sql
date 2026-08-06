-- SQLSpec Migration
-- Version: 20260806103012
-- Description: default last active at
-- Created: 2026-08-06T10:30:12.000000+00:00
-- Author: David Riegel <40246197+davidriegel@users.noreply.github.com>

-- name: migrate-20260806103012-up

ALTER TABLE users
    MODIFY last_active_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    ADD KEY idx_users_guest_active (is_guest, last_active_at);

UPDATE users
SET last_active_at = created_at
WHERE last_active_at IS NULL;

-- name: migrate-20260806103012-down

ALTER TABLE users
    MODIFY last_active_at TIMESTAMP NULL,
    DROP INDEX idx_users_guest_active;
