"""
DSA AutoGrader - Password Migration Script.

Migrates user passwords from legacy SHA-256 hashes to bcrypt.

Background:
- Old system: SHA-256 with fixed salt ("dsa_grader_salt_2026")
- New system: bcrypt with cost factor 12 (random salt)

Since SHA-256 is not reversible, users must re-enter passwords.
This script:
1. Identifies users with legacy SHA-256 password hashes
2. Marks them for password reset (sets a flag in the database)
3. On next login, prompts user to set a new password

Usage:
    python migrate_passwords.py [--dry-run] [--force-reset]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config import SETTINGS
from app.services.repository import GradingRepository
from app.utils.auth import hash_password

logger = logging.getLogger("dsa.migration")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# SHA-256 hash length is 64 chars (hex)
# bcrypt hash length is 60 chars (base64-like, starts with $2b$)
SHA256_HASH_LENGTH = 64
BCRYPT_HASH_PREFIX = "$2b$"


def is_legacy_hash(password_hash: str) -> bool:
    """Check if a password hash is the old SHA-256 format."""
    return len(password_hash) == SHA256_HASH_LENGTH and not password_hash.startswith(BCRYPT_HASH_PREFIX)


def is_bcrypt_hash(password_hash: str) -> bool:
    """Check if a password hash is already bcrypt."""
    return password_hash.startswith(BCRYPT_HASH_PREFIX)


def migrate_passwords(dry_run: bool = False, force_reset: bool = False) -> dict:
    """
    Migrate user passwords from SHA-256 to bcrypt.

    Args:
        dry_run: If True, only report what would be changed
        force_reset: If True, reset all legacy passwords to a default

    Returns:
        Dict with migration statistics
    """
    logger.info("=" * 60)
    logger.info("Password Migration: SHA-256 → bcrypt")
    logger.info("=" * 60)

    # Initialize repository
    repo = GradingRepository(
        sql_server_url=SETTINGS.database.sql_server_url,
        sqlite_file=SETTINGS.database.db_file,
    )
    repo.initialize()

    stats = {
        "total_users": 0,
        "already_bcrypt": 0,
        "legacy_sha256": 0,
        "migrated": 0,
        "errors": 0,
    }

    try:
        # Get all users (using raw SQL since repo may not have this method)
        db = repo._get_connection()
        cursor = db.cursor()

        # SQLite query
        cursor.execute("SELECT id, username, password_hash, role FROM users")
        users = cursor.fetchall()

        stats["total_users"] = len(users)
        logger.info("Found %d users to process", len(users))

        for user_id, username, password_hash, role in users:
            if is_bcrypt_hash(password_hash):
                stats["already_bcrypt"] += 1
                logger.info("  [OK] %s: Already using bcrypt", username)
                continue

            if is_legacy_hash(password_hash):
                stats["legacy_sha256"] += 1

                if dry_run:
                    logger.info("  [DRY RUN] %s: Would mark for password reset", username)
                    stats["migrated"] += 1
                    continue

                if force_reset:
                    # Set to a temporary password
                    temp_password = f"temp_{username}@2026"
                    new_hash = hash_password(temp_password)
                    logger.warning(
                        "  [RESET] %s: Password reset to '%s' (user must change)",
                        username, temp_password
                    )
                else:
                    # Mark for password reset (set a special prefix)
                    new_hash = f"[RESET_REQUIRED]_{password_hash}"
                    logger.info(
                        "  [MARKED] %s: Marked for password reset",
                        username
                    )

                # Update database
                cursor.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (new_hash, user_id)
                )
                stats["migrated"] += 1
            else:
                logger.warning("  [UNKNOWN] %s: Unrecognized hash format", username)
                stats["errors"] += 1

        # Commit changes
        if not dry_run:
            db.commit()
            logger.info("Changes committed to database")

    except Exception as e:
        logger.error("Migration failed: %s", e, exc_info=True)
        stats["errors"] += 1
    finally:
        repo.close()

    # Print summary
    logger.info("=" * 60)
    logger.info("Migration Summary:")
    logger.info("  Total users:    %d", stats["total_users"])
    logger.info("  Already bcrypt: %d", stats["already_bcrypt"])
    logger.info("  Legacy SHA-256: %d", stats["legacy_sha256"])
    logger.info("  Migrated:       %d", stats["migrated"])
    logger.info("  Errors:         %d", stats["errors"])
    logger.info("=" * 60)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate user passwords from SHA-256 to bcrypt")
    parser.add_argument("--dry-run", action="store_true", help="Only report, don't make changes")
    parser.add_argument("--force-reset", action="store_true", help="Reset legacy passwords to defaults")
    args = parser.parse_args()

    stats = migrate_passwords(dry_run=args.dry_run, force_reset=args.force_reset)

    if stats["errors"] > 0:
        sys.exit(1)
