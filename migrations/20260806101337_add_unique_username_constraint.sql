-- SQLSpec Migration
-- Version: 20260806101337
-- Description: add unique username constraint
-- Created: 2026-08-06T10:13:37.000000+00:00
-- Author: David Riegel <40246197+davidriegel@users.noreply.github.com>

-- name: migrate-20260806101337-up

ALTER TABLE users
    ADD UNIQUE KEY uq_users_username (username);

-- name: migrate-20260806101337-down

ALTER TABLE users
    DROP INDEX uq_users_username;
