"""
Cross-Platform PostgreSQL Backup Runner
Reads database configuration from app.core.config.settings, executes pg_dump,
and prunes backups older than 7 days.
"""
import os
import sys
import time
import subprocess
from pathlib import Path
from urllib.parse import urlparse

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import settings

def run_backup(backup_dir: str = "backups", retention_days: int = 7):
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"replybd_backup_{timestamp}.dump")

    # Parse database URL
    sync_url = settings.SYNC_DATABASE_URL or settings.DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", "")
    
    if "sqlite" in sync_url:
        print(f"[*] SQLite database detected. Copying SQLite file directly...")
        db_path = sync_url.replace("sqlite:///", "")
        if os.path.exists(db_path):
            import shutil
            shutil.copy2(db_path, backup_file)
            print(f"[+] Backup complete: {backup_file} ({os.path.getsize(backup_file)} bytes)")
            return backup_file
        else:
            print(f"[-] SQLite database file not found at {db_path}")
            return None

    parsed = urlparse(sync_url)
    db_name = parsed.path.lstrip("/")
    user = parsed.username or "postgres"
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = str(parsed.port or 5432)

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    cmd = [
        "pg_dump",
        "-h", host,
        "-p", port,
        "-U", user,
        "-F", "c",
        "-b",
        "-f", backup_file,
        db_name
    ]

    print(f"[*] Executing pg_dump for database '{db_name}' on {host}:{port}...")
    try:
        res = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        size_kb = os.path.getsize(backup_file) / 1024
        print(f"[+] PostgreSQL backup successful: {backup_file} ({size_kb:.1f} KB)")
    except FileNotFoundError:
        print("[-] pg_dump executable not found on PATH. Please ensure PostgreSQL client tools are installed.")
        return None
    except subprocess.CalledProcessError as e:
        print(f"[-] Backup failed with error: {e.stderr}")
        return None

    # Prune old backups
    cutoff = time.time() - (retention_days * 86400)
    for f in Path(backup_dir).glob("replybd_backup_*.dump"):
        if f.stat().st_mtime < cutoff:
            print(f"[*] Pruning expired backup: {f.name}")
            f.unlink()

    return backup_file

if __name__ == "__main__":
    run_backup()
