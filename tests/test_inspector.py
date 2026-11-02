"""Standard-library tests; original device firmware is not needed."""
import importlib.util
from pathlib import Path
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("inspector", ROOT / "tools" / "inspect_firmware.py")
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


class InspectorTest(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(inspector.DEFAULT_ROOTFS_OFFSET, 0x00380000)
        self.assertEqual(inspector.DEFAULT_ROOTFS_LENGTH, 20 * 1024 * 1024)

    def test_empty_uimage(self):
        self.assertFalse(inspector.inspect_uimage(bytes(0x80000 + 64))["found"])

    def test_empty_jffs(self):
        paths, inodes, mapping, summary = inspector.scan_jffs2(bytes(4096), 0, 4096)
        self.assertEqual(summary["node_type_counts"], {})
        self.assertEqual(paths[0]["path"], "/")

    def test_crc_repeatable(self):
        sample = b"OpenIPC static research"
        self.assertEqual(inspector.jffs_crc(sample), (zlib.crc32(sample, 0xFFFFFFFF) ^ 0xFFFFFFFF) & 0xFFFFFFFF)


if __name__ == "__main__":
    unittest.main()
