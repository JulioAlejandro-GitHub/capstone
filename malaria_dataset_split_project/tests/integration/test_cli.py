import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from malaria_split.cli import main


class CliTests(unittest.TestCase):
    def test_cli_audits_fixture(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            root = temp / "split"
            for split in ("train", "val", "test"):
                for class_name in ("parasitized", "uninfected"):
                    directory = root / split / class_name
                    directory.mkdir(parents=True)
                    (directory / "one.png").write_bytes(b"image")
            config = temp / "config.yaml"
            config.write_text(
                f"current_physical_split_root: {root}\n"
                "expected_splits: train,val,test\n"
                "expected_classes: parasitized,uninfected\n"
                "expected_extensions: .png,.jpg,.jpeg\n",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["audit-current-split", "--config", str(config)])
            payload = json.loads(output.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["total_image_files"], 6)
            self.assertEqual(payload["inspected_root"], str(root.resolve()))


if __name__ == "__main__":
    unittest.main()

