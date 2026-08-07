-- SQLSpec Migration
-- Version: 20260807143052
-- Description: add hard delete events
-- Created: 2026-08-07T14:30:52.000000+00:00
-- Author: David Riegel <40246197+davidriegel@users.noreply.github.com>

-- name: migrate-20260807143052-up

CREATE EVENT IF NOT EXISTS delete_soft_deleted_clothing
    ON SCHEDULE EVERY 1 DAY
    DO DELETE FROM clothing
       WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL 7 DAY;

CREATE EVENT IF NOT EXISTS delete_soft_deleted_outfits
    ON SCHEDULE EVERY 1 DAY
    DO DELETE FROM outfits
       WHERE deleted_at IS NOT NULL AND deleted_at < NOW() - INTERVAL 7 DAY;

-- name: migrate-20260807143052-down

DROP EVENT IF EXISTS delete_soft_deleted_clothing;
DROP EVENT IF EXISTS delete_soft_deleted_outfits;
