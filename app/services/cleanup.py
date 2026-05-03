__all__ = ["run_guest_cleanup"]

import os
from datetime import datetime, timedelta, timezone
from os import getenv
from app.core.database import Database
from app.core.logging import get_logger

INACTIVE_DAYS = int(getenv("CLEANUP_INACTIVE_DAYS", "90"))
MAX_DELETE_PER_RUN = int(getenv("CLEANUP_MAX_DELETE", "100"))
CLEANUP_LOCK_NAME = "drssed_cleanup_job"

STATIC_FOLDER = "static"
PROFILE_PICTURE_SUBDIR = "profile_pictures"
CLOTHING_SUBDIR = "clothing_images"
OUTFIT_SUBDIR = "outfit_collages"

logger = get_logger()

def run_guest_cleanup() -> None:
    with Database.getConnection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT GET_LOCK(%s, 0);", (CLEANUP_LOCK_NAME,))
        result = cursor.fetchone()
        
        if not result or not isinstance(result, tuple):
            logger.warning("Cleanup lock acquisition returned no result")
            return
        
        got_lock, = result
        
        if got_lock != 1:
            logger.info("Cleanup skipped: lock held by another worker")
            return
        
        try:
            _do_cleanup(conn, cursor)
        finally:
            cursor.execute("SELECT RELEASE_LOCK(%s);", (CLEANUP_LOCK_NAME,))
            cursor.fetchone()
            
def _do_cleanup(conn, cursor) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=INACTIVE_DAYS)
    
    logger.debug(f"Start cleanup", extra={"cutoff": cutoff.isoformat(), "max_delete": MAX_DELETE_PER_RUN})
    
    cursor.execute("SELECT user_id FROM users WHERE is_guest = TRUE AND last_active_at < %s LIMIT %s;",(cutoff, MAX_DELETE_PER_RUN))
    rows = cursor.fetchall()
    
    if not rows or not isinstance(rows, list):
        logger.debug("No inactive guest users found for cleanup")
        return
    
    if not all(isinstance(row, tuple) for row in rows):
        raise ValueError("Expected rows to be a list of tuples")
    
    user_ids = [row[0] for row in rows]
    
    if not all(isinstance(user_id, str) for user_id in user_ids):
        raise ValueError("Expected all user_ids to be strings")
    
    deleted_users = 0
    failed_users = 0
    total_files_deleted = 0
    
    for user_id in user_ids:
        try:
            files_deleted = _delete_user(conn, cursor, user_id)
            deleted_users += 1
            total_files_deleted += files_deleted
        except Exception as e:
            conn.rollback()
            failed_users += 1
            logger.error("Failed to delete user during cleanup", extra={"user_id": user_id, "error": str(e)})
    
    logger.debug("Cleanup complete", extra={"deleted_users": deleted_users, "failed_users": failed_users, "total_files_deleted": total_files_deleted})
    
def _delete_user(conn, cursor, user_id: str) -> int:
    files_to_delete = _collect_user_files(cursor, user_id)
    
    cursor.execute("DELETE FROM users WHERE user_id = %s;", (user_id,))
    conn.commit()
    
    deleted = _delete_files(files_to_delete)
    
    return deleted

def _collect_user_files(cursor, user_id: str) -> list:
    paths = []
    
    cursor.execute("SELECT image_id FROM clothing WHERE user_id = %s AND image_id IS NOT NULL;", (user_id,))
    result = cursor.fetchall()
    
    if not result or not isinstance(result, list):
        return paths
    
    for row in result:
        if not isinstance(row, tuple):
            raise ValueError("Expected row to be a tuple")
        
        image_id, = row
        
        if not isinstance(image_id, str):
            raise ValueError("Expected image_id to be a string")
        
        filename = f"{image_id}.webp"
        paths.append(os.path.join(STATIC_FOLDER, CLOTHING_SUBDIR, filename))
    
    cursor.execute("SELECT outfit_id FROM outfits WHERE user_id = %s;", (user_id,))
    for row in cursor.fetchall():
        if not isinstance(row, tuple):
            raise ValueError("Expected row to be a tuple")

        outfit_id, = row

        if not isinstance(outfit_id, str):
            raise ValueError("Expected outfit_id to be a string")

        filename = f"{outfit_id}.webp"
        paths.append(os.path.join(STATIC_FOLDER, OUTFIT_SUBDIR, filename))
    
    return paths

def _delete_files(paths: list) -> int:
    deleted = 0
    for path in paths:
        try:
            os.remove(path)
            deleted += 1
        except FileNotFoundError:
            pass
    return deleted