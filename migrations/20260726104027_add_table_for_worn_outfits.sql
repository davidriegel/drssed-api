-- SQLSpec Migration
-- Version: 20260726104027
-- Description: add table for worn outfits
-- Created: 2026-07-26T10:40:27.944468+00:00
-- Author: David Riegel <40246197+davidriegel@users.noreply.github.com>

-- name: migrate-20260726104027-up
CREATE TABLE outfit_wears (
    wear_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    outfit_id VARCHAR(36) NOT NULL,
    worn_on TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    feels_like FLOAT NULL,
    temperature FLOAT NULL,
    weather VARCHAR(20) NULL,
    occasion VARCHAR(20) NULL,
    rating TINYINT NULL,
    note VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    active_worn_date DATE
        GENERATED ALWAYS AS (IF(deleted_at IS NULL, DATE(worn_on), NULL)) STORED,
    PRIMARY KEY (wear_id),
    UNIQUE KEY uq_outfit_wears_day (user_id, outfit_id, active_worn_date),
    KEY idx_outfit_wears_user_date (user_id, worn_on DESC),
    KEY idx_outfit_wears_user_updated (user_id, updated_at),
    CONSTRAINT fk_outfit_user
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_wear_outfit
        FOREIGN KEY (outfit_id) REFERENCES outfits(outfit_id) ON DELETE CASCADE,
    CONSTRAINT chk_wear_rating
        CHECK (rating IS NULL OR rating BETWEEN 1 AND 5)
) ENGINE=InnoDB;

CREATE TABLE outfit_wear_clothing (
    wear_id VARCHAR(36) NOT NULL,
    clothing_id VARCHAR(36) NOT NULL,
    PRIMARY KEY (wear_id, clothing_id),
    KEY idx_outfit_wear_clothing_clothing (clothing_id),
    CONSTRAINT fk_outfit_wear_clothing_wear
        FOREIGN KEY (wear_id) REFERENCES outfit_wears(wear_id) ON DELETE CASCADE,
    CONSTRAINT fk_outfit_wear_clothing_clothing
        FOREIGN KEY (clothing_id) REFERENCES clothing(clothing_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- name: migrate-20260726104027-down

DROP TABLE outfit_wear_clothing;
DROP TABLE outfit_wears;
