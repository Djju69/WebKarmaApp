"""
Database backup script.
"""
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
import logging
from typing import Optional, List

from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("backup.log"),
    ],
)
logger = logging.getLogger(__name__)

# Backup directory
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "backups"))
BACKUP_DIR.mkdir(exist_ok=True, parents=True)

# Retention policy (days to keep backups)
RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))


def create_backup() -> Optional[Path]:
    """Create a database backup."""
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL is not set")
        return None
    
    # Parse database URL
    from sqlalchemy.engine.url import make_url
    db_url = make_url(settings.DATABASE_URL)
    
    # Generate backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backup_{timestamp}.sql"
    
    try:
        # Build pg_dump command
        cmd = [
            "pg_dump",
            f"--dbname={db_url.database}",
            f"--username={db_url.username or 'postgres'}",
            f"--host={db_url.host or 'localhost'}",
            f"--port={db_url.port or '5432'}",
            "--format=plain",
            "--no-owner",
            "--no-privileges",
            "--no-tablespaces",
            f"--file={backup_file}",
        ]
        
        # Set password if provided
        env = os.environ.copy()
        if db_url.password:
            env["PGPASSWORD"] = db_url.password
        
        # Run pg_dump
        logger.info(f"Creating backup: {backup_file}")
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        
        duration = time.time() - start_time
        file_size = backup_file.stat().st_size / (1024 * 1024)  # MB
        
        logger.info(
            f"Backup completed successfully. "
            f"Size: {file_size:.2f} MB, "
            f"Duration: {duration:.2f} seconds"
        )
        
        return backup_file
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup failed: {e.stderr}")
        if backup_file.exists():
            backup_file.unlink()
        return None
    except Exception as e:
        logger.error(f"Unexpected error during backup: {str(e)}")
        if backup_file.exists():
            backup_file.unlink()
        return None


def cleanup_old_backups() -> List[Path]:
    """Remove old backup files based on retention policy."""
    now = time.time()
    deleted = []
    
    for backup_file in BACKUP_DIR.glob("backup_*.sql"):
        file_age_days = (now - backup_file.stat().st_mtime) / (24 * 3600)
        
        if file_age_days > RETENTION_DAYS:
            try:
                backup_file.unlink()
                deleted.append(backup_file)
                logger.info(f"Deleted old backup: {backup_file.name}")
            except Exception as e:
                logger.error(f"Failed to delete {backup_file}: {str(e)}")
    
    return deleted


def list_backups() -> List[Path]:
    """List all available backups."""
    return sorted(BACKUP_DIR.glob("backup_*.sql"), key=os.path.getmtime, reverse=True)


def restore_backup(backup_file: Path) -> bool:
    """Restore database from backup."""
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL is not set")
        return False
    
    if not backup_file.exists():
        logger.error(f"Backup file not found: {backup_file}")
        return False
    
    # Parse database URL
    from sqlalchemy.engine.url import make_url
    db_url = make_url(settings.DATABASE_URL)
    
    try:
        # Build psql command
        cmd = [
            "psql",
            f"--dbname={db_url.database}",
            f"--username={db_url.username or 'postgres'}",
            f"--host={db_url.host or 'localhost'}",
            f"--port={db_url.port or '5432'}",
            "--single-transaction",
            "--set=ON_ERROR_STOP=1",
            f"--file={backup_file}",
        ]
        
        # Set password if provided
        env = os.environ.copy()
        if db_url.password:
            env["PGPASSWORD"] = db_url.password
        
        # Run psql
        logger.info(f"Restoring from backup: {backup_file}")
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        
        duration = time.time() - start_time
        logger.info(f"Restore completed successfully in {duration:.2f} seconds")
        
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Restore failed: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during restore: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Database backup and restore utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Create backup command
    create_parser = subparsers.add_parser("create", help="Create a new backup")
    
    # List backups command
    list_parser = subparsers.add_parser("list", help="List available backups")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_file", help="Path to backup file")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup old backups")
    
    args = parser.parse_args()
    
    if args.command == "create":
        backup_file = create_backup()
        if backup_file:
            print(f"Backup created: {backup_file}")
        else:
            print("Backup failed")
            exit(1)
    
    elif args.command == "list":
        backups = list_backups()
        if not backups:
            print("No backups found")
        else:
            print("Available backups:")
            for i, backup in enumerate(backups, 1):
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                size_mb = backup.stat().st_size / (1024 * 1024)
                print(f"{i}. {backup.name} - {mtime} - {size_mb:.2f} MB")
    
    elif args.command == "restore":
        if restore_backup(Path(args.backup_file)):
            print("Restore completed successfully")
        else:
            print("Restore failed")
            exit(1)
    
    elif args.command == "cleanup":
        deleted = cleanup_old_backups()
        if deleted:
            print(f"Deleted {len(deleted)} old backups")
        else:
            print("No old backups to delete")
    
    else:
        parser.print_help()
        exit(1)
