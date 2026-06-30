__all__ = [
    "run_guest_cleanup",
    "run_temp_cleanup",
    "run_orphan_files_cleanup",
    "create_cleanup_jobs",
]

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apscheduler.triggers.cron import CronTrigger
from flask import current_app

from app.core.database import get_session
from app.core.logging import get_logger
from app.core.scheduler import JobSpec
from app.persistence.queries import clothing as clothing_queries
from app.persistence.queries import outfit as outfit_queries
from app.persistence.queries import system as system_queries
from app.persistence.queries import user as user_queries

logger = get_logger()

# Config

INACTIVE_DAYS = int(os.getenv("CLEANUP_INACTIVE_DAYS", "90"))
MAX_DELETE_PER_RUN = int(os.getenv("CLEANUP_MAX_DELETE", "100"))
ORPHAN_FILE_GRACE_HOURS = int(os.getenv("CLEANUP_ORPHAN_GRACE_HOURS", "24"))
ORPHAN_MAX_DELETE_PER_RUN = int(os.getenv("CLEANUP_ORPHAN_MAX_DELETE", "500"))
TEMP_FILE_MAX_AGE_HOURS = 24

GUEST_CLEANUP_LOCK = "drssed_cleanup_job"
ORPHAN_CLEANUP_LOCK = "drssed_orphan_cleanup_job"

PROFILE_PICTURE_SUBDIR = "profile_pictures"
CLOTHING_SUBDIR = "clothing_images"
OUTFIT_SUBDIR = "outfit_collages"
TEMP_SUBDIR = "temp"


def _get_static_folder() -> Path:
    folder = current_app.static_folder
    if not folder:
        raise RuntimeError("Flask static_folder is not configured")
    return Path(folder)


# === Job: Guest cleanup ===

def run_guest_cleanup() -> None:
    """Deletes inactive guest accounts and their associated files."""
    with get_session() as session:
        if not system_queries.try_acquire_lock(session, GUEST_CLEANUP_LOCK):
            logger.debug("Guest cleanup skipped: lock held by another worker")
            return
        
        try:
            _do_guest_cleanup(session)
        finally:
            system_queries.release_lock(session, GUEST_CLEANUP_LOCK)


def _do_guest_cleanup(session) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=INACTIVE_DAYS)
    
    logger.debug(
        "Start inactive guest cleanup",
        extra={"cutoff": cutoff.isoformat(), "max_delete": MAX_DELETE_PER_RUN},
    )
    
    inactive_users = user_queries.get_inactive_guest_ids(session, cutoff, MAX_DELETE_PER_RUN)
    
    if not inactive_users:
        logger.debug("No inactive guest users found for cleanup")
        return
    
    deleted_users = 0
    failed_users = 0
    total_files_deleted = 0
    
    for user in inactive_users:
        try:
            files_deleted = _delete_user_and_files(session, user.user_id)
            session.commit()
            deleted_users += 1
            total_files_deleted += files_deleted
        except Exception as e:
            session.rollback()
            failed_users += 1
            logger.error(
                "Failed to delete user during cleanup",
                extra={"user_id": user.user_id, "error": str(e)},
            )
    
    logger.debug(
        "Inactive guest cleanup complete",
        extra={
            "deleted_users": deleted_users,
            "failed_users": failed_users,
            "total_files_deleted": total_files_deleted,
        },
    )


def _delete_user_and_files(session, user_id: str) -> int:
    """Collects file paths, deletes the user row, then deletes the files."""
    files_to_delete = _collect_user_files(session, user_id)
    user_queries.delete_by_id_in_session(session, user_id)
    
    deleted = _delete_files(files_to_delete)
    return deleted


def _collect_user_files(session, user_id: str) -> list[str]:
    static_root = _get_static_folder()
    paths = []
    
    for ref in clothing_queries.get_image_ids_for_user(session, user_id):
        paths.append(str(static_root / CLOTHING_SUBDIR / f"{ref.file_id}.webp"))
    
    for ref in outfit_queries.get_outfit_ids_for_user(session, user_id):
        paths.append(str(static_root / OUTFIT_SUBDIR / f"{ref.file_id}.webp"))
    
    return paths


def _delete_files(paths: list[str]) -> int:
    deleted = 0
    for path in paths:
        try:
            os.remove(path)
            deleted += 1
        except FileNotFoundError:
            pass
    return deleted


# === Job: Temp file cleanup ===

def run_temp_cleanup() -> None:
    """Deletes temp files older than TEMP_FILE_MAX_AGE_HOURS."""
    temp_dir = _get_static_folder() / TEMP_SUBDIR
    
    if not temp_dir.exists():
        logger.warning("Temp cleanup skipped: directory does not exist")
        return
    
    cutoff = (datetime.now() - timedelta(hours=TEMP_FILE_MAX_AGE_HOURS)).timestamp()
    
    logger.debug(
        "Start orphaned temporary file cleanup",
        extra={"max_age_hours": TEMP_FILE_MAX_AGE_HOURS},
    )
    
    deleted = 0
    skipped = 0
    failed = 0
    
    for entry in temp_dir.iterdir():
        if not entry.is_file():
            continue
        
        try:
            if entry.stat().st_mtime >= cutoff:
                skipped += 1
                continue
            
            entry.unlink(missing_ok=True)
            deleted += 1
        except Exception as e:
            failed += 1
            logger.error(f"Failed to delete temporary file {entry.name}: {e}")
    
    logger.debug(
        "Orphaned temporary file cleanup complete",
        extra={"deleted": deleted, "skipped": skipped, "failed": failed},
    )


# === Job: Orphan files cleanup ===

def run_orphan_files_cleanup() -> None:
    """Deletes image files on disk that aren't referenced in the database."""
    with get_session() as session:
        if not system_queries.try_acquire_lock(session, ORPHAN_CLEANUP_LOCK):
            logger.debug("Orphan files cleanup skipped: lock held by another worker")
            return
        
        try:
            _do_orphan_cleanup(
                subdir=CLOTHING_SUBDIR,
                referenced=set(
                    f"{ref.file_id}.webp"
                    for ref in clothing_queries.get_all_referenced_image_ids(session)
                ),
            )
            _do_orphan_cleanup(
                subdir=OUTFIT_SUBDIR,
                referenced=set(
                    f"{ref.file_id}.webp"
                    for ref in outfit_queries.get_all_outfit_ids(session)
                ),
            )
            _do_orphan_cleanup(
                subdir=PROFILE_PICTURE_SUBDIR,
                referenced=set(
                    f"{ref.file_id}.webp"
                    for ref in user_queries.get_referenced_profile_pictures(session)
                    if not ref.file_id.startswith("default/")
                ),
            )
        finally:
            system_queries.release_lock(session, ORPHAN_CLEANUP_LOCK)


def _do_orphan_cleanup(subdir: str, referenced: set[str]) -> None:
    directory = _get_static_folder() / subdir
    
    if not directory.exists():
        logger.warning(
            "Orphan cleanup skipped: directory does not exist",
            extra={"subdir": subdir},
        )
        return
    
    cutoff = (datetime.now() - timedelta(hours=ORPHAN_FILE_GRACE_HOURS)).timestamp()
    
    logger.debug(
        "Start orphan files cleanup",
        extra={
            "subdir": subdir,
            "grace_hours": ORPHAN_FILE_GRACE_HOURS,
            "max_delete": ORPHAN_MAX_DELETE_PER_RUN,
        },
    )
    
    scanned = 0
    deleted = 0
    skipped_referenced = 0
    skipped_grace = 0
    failed = 0
    bytes_freed = 0
    
    for entry in directory.iterdir():
        if not entry.is_file():
            continue
        
        scanned += 1
        
        if entry.name in referenced:
            skipped_referenced += 1
            continue
        
        try:
            stat = entry.stat()
            
            if stat.st_mtime >= cutoff:
                skipped_grace += 1
                continue
            
            if deleted >= ORPHAN_MAX_DELETE_PER_RUN:
                logger.info(
                    "Orphan cleanup hit per-run limit",
                    extra={"subdir": subdir, "limit": ORPHAN_MAX_DELETE_PER_RUN},
                )
                break
            
            size = stat.st_size
            entry.unlink(missing_ok=True)
            deleted += 1
            bytes_freed += size
        except Exception as e:
            failed += 1
            logger.error(
                "Failed to delete orphan file",
                extra={"subdir": subdir, "name": entry.name, "error": str(e)},
            )
    
    logger.debug(
        "Orphan files cleanup complete",
        extra={
            "subdir": subdir,
            "scanned": scanned,
            "referenced": len(referenced),
            "deleted": deleted,
            "skipped_referenced": skipped_referenced,
            "skipped_grace": skipped_grace,
            "failed": failed,
            "bytes_freed": bytes_freed,
        },
    )


# === Job scheduler registration ===

def create_cleanup_jobs() -> list[JobSpec]:
    """Define all cleanup-related scheduled jobs."""
    return [
        JobSpec(
            func=run_guest_cleanup,
            trigger=CronTrigger(hour=3, minute=0),
            job_id="cleanup_inactive_guests",
            name="Cleanup inactive guest accounts",
        ),
        JobSpec(
            func=run_temp_cleanup,
            trigger=CronTrigger(hour="*/6", minute=15),
            job_id="cleanup_temp_files",
            name="Cleanup orphaned temp files",
        ),
        JobSpec(
            func=run_orphan_files_cleanup,
            trigger=CronTrigger(hour=3, minute=30),
            job_id="cleanup_orphan_files",
            name="Cleanup orphaned image files",
        ),
    ]