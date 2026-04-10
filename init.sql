-- Users
CREATE TABLE
    IF NOT EXISTS users (
        user_id VARCHAR(36) PRIMARY KEY,
        is_guest BOOLEAN DEFAULT TRUE,
        username VARCHAR(32) UNIQUE DEFAULT NULL,
        email VARCHAR(255) UNIQUE DEFAULT NULL,
        password VARCHAR(97) DEFAULT NULL,
        profile_picture VARCHAR(255) DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    
-- Authentication tokens

CREATE TABLE
    IF NOT EXISTS refresh_tokens (
        user_id VARCHAR(36) NOT NULL,
        refresh_token VARCHAR(24) PRIMARY KEY,
        refresh_token_expiry TIMESTAMP DEFAULT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );

CREATE EVENT IF NOT EXISTS delete_expired_refresh_tokens
ON SCHEDULE EVERY 1 DAY
DO
DELETE FROM refresh_tokens
WHERE refresh_token_expiry < NOW();

-- Clothes

CREATE TABLE
    IF NOT EXISTS clothing (
        clothing_id VARCHAR(36) PRIMARY KEY,
        is_public BOOLEAN DEFAULT TRUE,
        name VARCHAR(50) NOT NULL,
        category VARCHAR(50) NOT NULL,
        image_id VARCHAR(36) UNIQUE NOT NULL,
        user_id VARCHAR(36) NOT NULL,
        color CHAR(7) NOT NULL,
        description VARCHAR(255) DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        deleted_at TIMESTAMP DEFAULT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS clothing_seasons (
        clothing_id VARCHAR(36) NOT NULL,
        season ENUM ('SPRING', 'SUMMER', 'AUTUMN', 'WINTER') NOT NULL,
        FOREIGN KEY (clothing_id) REFERENCES clothing (clothing_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS clothing_tags (
        clothing_id VARCHAR(36) NOT NULL,
        tag VARCHAR(50) NOT NULL,
        FOREIGN KEY (clothing_id) REFERENCES clothing (clothing_id) ON DELETE CASCADE
    );

-- Outfits
CREATE TABLE
    IF NOT EXISTS outfits (
        outfit_id VARCHAR(36) PRIMARY KEY,
        is_public BOOLEAN DEFAULT TRUE,
        name VARCHAR(50) NOT NULL,
        is_favorite BOOLEAN DEFAULT FALSE,
        user_id VARCHAR(36) NOT NULL,
        description VARCHAR(255) DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        deleted_at TIMESTAMP DEFAULT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS outfit_seasons (
        outfit_id VARCHAR(36) NOT NULL,
        season ENUM ('SPRING', 'SUMMER', 'AUTUMN', 'WINTER') NOT NULL,
        PRIMARY KEY (outfit_id, season),
        FOREIGN KEY (outfit_id) REFERENCES outfits (outfit_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS outfit_tags (
        outfit_id VARCHAR(36) NOT NULL,
        tag VARCHAR(50) NOT NULL,
        PRIMARY KEY (outfit_id, tag),
        INDEX (tag),
        FOREIGN KEY (outfit_id) REFERENCES outfits (outfit_id) ON DELETE CASCADE
    );

CREATE TABLE
    IF NOT EXISTS outfit_clothing (
        outfit_id VARCHAR(36) NOT NULL,
        clothing_id VARCHAR(36) NOT NULL,
        position_x FLOAT NOT NULL,
        position_y FLOAT NOT NULL,
        z_index INT NOT NULL,
        scale FLOAT NOT NULL,
        rotation FLOAT NOT NULL,
        PRIMARY KEY (outfit_id, clothing_id),
        INDEX (clothing_id),
        FOREIGN KEY (outfit_id) REFERENCES outfits (outfit_id) ON DELETE CASCADE,
        FOREIGN KEY (clothing_id) REFERENCES clothing (clothing_id) ON DELETE CASCADE
    );