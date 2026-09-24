"""
Tests for Policy Snapshot Integrity & Rollback Security.
Verifies validation of snapshot IDs against directory traversal, atomic file replacement,
and thread locking.
"""

import json
from pathlib import Path
import tempfile
import unittest
from src.utils.storage_safety import (
    StorageSecurityError,
    get_snapshot_lock,
    safe_atomic_write_json,
    validate_snapshot_id,
)


class TestSnapshotSecurity(unittest.TestCase):
    def test_valid_snapshot_id_accepted(self):
        valid = "snapshot_20260924_v1"
        self.assertEqual(validate_snapshot_id(valid), valid)

    def test_traversal_snapshot_id_rejected(self):
        traversal = "../../../../etc/passwd"
        with self.assertRaises(StorageSecurityError):
            validate_snapshot_id(traversal)

    def test_null_byte_snapshot_id_rejected(self):
        null_byte = "snapshot_v1\x00_malicious"
        with self.assertRaises(StorageSecurityError):
            validate_snapshot_id(null_byte)

    def test_special_characters_snapshot_id_rejected(self):
        special = "snapshot; rm -rf /"
        with self.assertRaises(StorageSecurityError):
            validate_snapshot_id(special)

    def test_safe_atomic_write_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "active_version.json"
            data = {"active_snapshot": "snapshot_20260924_v1", "version": 1}
            safe_atomic_write_json(target, data, base_dir=tmp_dir)

            self.assertTrue(target.exists())
            with open(target, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded["active_snapshot"], "snapshot_20260924_v1")

    def test_atomic_write_escapes_base_dir_blocked(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir) / "allowed_base"
            base.mkdir()
            target = Path(tmp_dir) / "escaped.json"
            with self.assertRaises(StorageSecurityError):
                safe_atomic_write_json(target, {"data": 1}, base_dir=base)

    def test_snapshot_lock_available(self):
        lock = get_snapshot_lock()
        acquired = lock.acquire(timeout=1.0)
        self.assertTrue(acquired)
        lock.release()


if __name__ == "__main__":
    unittest.main()
