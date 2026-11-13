import os
import shutil
import tempfile
import subprocess
import pytest
from pathlib import Path


def test_backup_and_restore_cycle():
    """Verify scripts/backup.sh and scripts/restore.sh function correctly."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    backup_script = repo_root / "scripts" / "backup.sh"
    restore_script = repo_root / "scripts" / "restore.sh"

    assert backup_script.exists()
    assert restore_script.exists()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_backup_dir = Path(tmpdir) / "test_backups"
        tmp_backup_dir.mkdir(parents=True, exist_ok=True)

        # 1. Run backup
        proc_backup = subprocess.run(
            [str(backup_script), str(tmp_backup_dir)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        assert proc_backup.returncode == 0, f"Backup failed: {proc_backup.stderr}"
        assert "Backup created successfully" in proc_backup.stdout

        # Find generated backup archive
        archives = list(tmp_backup_dir.glob("ruby_backup_*.tar.gz"))
        assert len(archives) >= 1
        archive_path = archives[0]
        assert archive_path.stat().st_size > 0

        # 2. Test restore verification in an isolated temporary directory
        tmp_restore_target = Path(tmpdir) / "restore_dest"
        tmp_restore_target.mkdir(parents=True, exist_ok=True)

        # Running restore on archive into isolated target directory
        proc_restore = subprocess.run(
            [str(restore_script), str(archive_path), "--force", str(tmp_restore_target)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        assert proc_restore.returncode == 0, f"Restore failed: {proc_restore.stderr}"
        assert "System restore completed successfully" in proc_restore.stdout
        assert (tmp_restore_target / "data" / "ruby.db").exists()
