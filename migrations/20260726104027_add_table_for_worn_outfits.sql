-- SQLSpec Migration
-- Version: 20260726104027
-- Description: add table for worn outfits
-- Created: 2026-07-26T10:40:27.944468+00:00
-- Author: David Riegel <40246197+davidriegel@users.noreply.github.com>

-- name: migrate-20260726104027-up
CREATE TABLE outfit_wears (
    user_id VARCHAR(36) NOT NULL,
    outfit_id VARCHAR(36) NOT NULL,
    worn_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    feels_like REAL NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_outfit_user
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_wear_outfit
        FOREIGN KEY (outfit_id) REFERENCES outfits(outfit_id) ON DELETE CASCADE
);

CREATE INDEX idx_outfit_wears_user_date ON outfit_wears (user_id, worn_on DESC);
CREATE UNIQUE INDEX uq_outfit_wears_day ON outfit_wears (user_id, outfit_id, worn_on);

-- name: migrate-20260726104027-down

DROP TABLE outfit_wears;
