-- SQLSpec Migration
-- Version: 20260806094512
-- Description: uppercase season enums
-- Created: 2026-08-06T09:45:12.000000+00:00
-- Author: David Riegel <40246197+davidriegel@users.noreply.github.com>

-- name: migrate-20260806094512-up

ALTER TABLE clothing_seasons
    MODIFY season ENUM('SPRING','SUMMER','AUTUMN','WINTER') NOT NULL;

ALTER TABLE outfit_seasons
    MODIFY season ENUM('SPRING','SUMMER','AUTUMN','WINTER') NOT NULL;

-- name: migrate-20260806094512-down

ALTER TABLE clothing_seasons
    MODIFY season ENUM('spring','summer','autumn','winter') NOT NULL;

ALTER TABLE outfit_seasons
    MODIFY season ENUM('spring','summer','autumn','winter') NOT NULL;
