-- SQLSpec Migration
-- Version: 20260719140952
-- Description: drop description columns
-- Created: 2026-07-19T14:09:52.448858+00:00
-- Author: David Riegel <40246197+davidriegel@users.noreply.github.com>

-- name: migrate-20260719140952-up

SET @drop_clothing_description := IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = 'clothing' AND column_name = 'description'),
    'ALTER TABLE clothing DROP COLUMN description',
    'DO 0');
PREPARE stmt FROM @drop_clothing_description;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @drop_outfits_description := IF(
    EXISTS(SELECT 1 FROM information_schema.columns
           WHERE table_schema = DATABASE() AND table_name = 'outfits' AND column_name = 'description'),
    'ALTER TABLE outfits DROP COLUMN description',
    'DO 0');
PREPARE stmt FROM @drop_outfits_description;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- name: migrate-20260719140952-down

ALTER TABLE clothing
    ADD description VARCHAR(255) NULL;

ALTER TABLE outfits
    ADD description VARCHAR(255) NULL;
