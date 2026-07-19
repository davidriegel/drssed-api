-- SQLSpec Migration
-- Version: 20260719140952
-- Description: drop description columns
-- Created: 2026-07-19T14:09:52.448858+00:00
-- Author: David Riegel <40246197+davidriegel@users.noreply.github.com>

-- name: migrate-20260719140952-up
ALTER TABLE clothing
    DROP COLUMN description;

ALTER TABLE outfits
    DROP COLUMN description;

-- name: migrate-20260719140952-down
ALTER TABLE clothing
    ADD description VARCHAR(255) NULL;

ALTER TABLE outfits
    ADD description VARCHAR(255) NULL;
