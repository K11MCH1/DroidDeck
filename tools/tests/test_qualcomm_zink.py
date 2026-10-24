import hashlib
import json
from pathlib import Path
import unittest

QUALCOMM = Path(__file__).resolve().parents[1] / "qualcomm"
PATCH = "zink-qualcomm-color-write-enable.patch"


class QualcommZinkTest(unittest.TestCase):
    def test_the_build_applies_the_color_write_patch(self):
        self.assertIn(f"'{PATCH}'", (QUALCOMM / "build_zink.py").read_text())
        patch = (QUALCOMM / PATCH).read_text()
        self.assertIn("+   if (zink_driverid(screen) == VK_DRIVER_ID_QUALCOMM_PROPRIETARY)", patch)
        self.assertIn("+      screen->info.have_EXT_color_write_enable = false;", patch)

    def test_the_runtime_pins_a_build_with_the_patch(self):
        files = {f["path"]: f["sha256"] for f in json.loads((QUALCOMM / "runtime.json").read_text())["mesa"]["files"]}
        self.assertEqual(files.get("licenses/" + PATCH), hashlib.sha256((QUALCOMM / PATCH).read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
