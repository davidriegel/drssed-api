-- -----------------------------------------------------------------------------
-- Users & Auth
-- -----------------------------------------------------------------------------

CREATE TABLE
    IF NOT EXISTS users (
    user_id VARCHAR(36) NOT NULL,
    is_guest TINYINT(1) NOT NULL DEFAULT 0,
    username VARCHAR(32) NOT NULL,
    email VARCHAR(255) NULL,
    password VARCHAR(97) NULL,
    profile_picture VARCHAR(255) NULL,
    apple_user_id VARCHAR(255) NULL,
    email_verified_at TIMESTAMP NULL,
    preferred_language CHAR(2) NULL,
    last_active_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_users_email (email),
    UNIQUE KEY uq_users_apple_user_id (apple_user_id)
) ENGINE=InnoDB;

CREATE TABLE
    IF NOT EXISTS email_verifications (
    token VARCHAR(43) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    email VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (token),
    KEY idx_email_verifications_user (user_id),
    KEY idx_email_verifications_expires (expires_at),
    CONSTRAINT fk_email_verifications_user 
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE
    IF NOT EXISTS refresh_tokens (
    refresh_token VARCHAR(24) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    refresh_token_expiry TIMESTAMP NULL,
    PRIMARY KEY (refresh_token),
    KEY idx_refresh_tokens_user (user_id),
    CONSTRAINT fk_refresh_tokens_user 
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Clothing
-- -----------------------------------------------------------------------------

CREATE TABLE
    IF NOT EXISTS clothing (
    clothing_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(50) NOT NULL,
    category VARCHAR(50) NOT NULL,
    sub_category VARCHAR(50) NOT NULL,
    image_id VARCHAR(36) NOT NULL,
    color CHAR(7) NOT NULL,
    description VARCHAR(255) NULL,
    is_public TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    PRIMARY KEY (clothing_id),
    KEY idx_clothing_user_deleted (user_id, deleted_at),
    KEY idx_clothing_user_cat_deleted (user_id, category, deleted_at),
    CONSTRAINT fk_clothing_user 
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
) ENGINE=InnoDB;

CREATE TABLE
    IF NOT EXISTS clothing_tags (
    clothing_id VARCHAR(36) NOT NULL,
    tag VARCHAR(50) NOT NULL,
    PRIMARY KEY (clothing_id, tag),
    CONSTRAINT fk_clothing_tags_clothing 
        FOREIGN KEY (clothing_id) REFERENCES clothing(clothing_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE
    IF NOT EXISTS clothing_seasons (
    clothing_id VARCHAR(36) NOT NULL,
    season ENUM('spring','summer','autumn','winter') NOT NULL,
    PRIMARY KEY (clothing_id, season),
    CONSTRAINT fk_clothing_seasons_clothing 
        FOREIGN KEY (clothing_id) REFERENCES clothing(clothing_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Outfits
-- -----------------------------------------------------------------------------

CREATE TABLE
    IF NOT EXISTS outfits (
    outfit_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(255) NULL,
    is_favorite TINYINT(1) NOT NULL DEFAULT 0,
    is_public TINYINT(1) NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    PRIMARY KEY (outfit_id),
    KEY idx_outfits_user_deleted (user_id, deleted_at),
    CONSTRAINT fk_outfits_user 
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE
    IF NOT EXISTS outfit_clothing (
    outfit_id VARCHAR(36) NOT NULL,
    clothing_id VARCHAR(36) NOT NULL,
    position_x FLOAT NOT NULL,
    position_y FLOAT NOT NULL,
    z_index INT NOT NULL DEFAULT 0,
    scale FLOAT NOT NULL DEFAULT 1.0,
    rotation FLOAT NOT NULL DEFAULT 0.0,
    PRIMARY KEY (outfit_id, clothing_id),
    KEY idx_outfit_clothing_clothing (clothing_id),
    CONSTRAINT fk_outfit_clothing_outfit 
        FOREIGN KEY (outfit_id) REFERENCES outfits(outfit_id) ON DELETE CASCADE,
    CONSTRAINT fk_outfit_clothing_clothing 
        FOREIGN KEY (clothing_id) REFERENCES clothing(clothing_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE
    IF NOT EXISTS outfit_tags (
    outfit_id VARCHAR(36) NOT NULL,
    tag VARCHAR(50) NOT NULL,
    PRIMARY KEY (outfit_id, tag),
    CONSTRAINT fk_outfit_tags_outfit 
        FOREIGN KEY (outfit_id) REFERENCES outfits(outfit_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE
    IF NOT EXISTS outfit_seasons (
    outfit_id VARCHAR(36) NOT NULL,
    season ENUM('spring','summer','autumn','winter') NOT NULL,
    PRIMARY KEY (outfit_id, season),
    CONSTRAINT fk_outfit_seasons_outfit 
        FOREIGN KEY (outfit_id) REFERENCES outfits(outfit_id) ON DELETE CASCADE
) ENGINE=InnoDB;