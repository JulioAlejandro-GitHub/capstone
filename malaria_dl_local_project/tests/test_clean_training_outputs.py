import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import clean_training_outputs as cleaner


class CleanTrainingOutputsTests(unittest.TestCase):
    def make_project(self, temp_dir):
        project_root = Path(temp_dir) / "project"
        outputs_dir = project_root / "outputs"
        outputs_dir.mkdir(parents=True)
        return project_root, outputs_dir

    def test_dry_run_no_elimina_archivos(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root, outputs_dir = self.make_project(temp_dir)
            model_path = outputs_dir / "custom_cnn" / "best_model.keras"
            model_path.parent.mkdir()
            model_path.write_text("model", encoding="utf-8")

            with mock.patch.object(cleaner, "PROJECT_ROOT", project_root):
                result = cleaner.clean_training_outputs(
                    outputs_dir=outputs_dir,
                    execute=False,
                    confirm=None,
                    backup_before=False,
                    backup_dir=Path(temp_dir) / "backups",
                    keep_directory_structure=True,
                )

            self.assertTrue(model_path.exists())
            self.assertEqual(result["mode"], "DRY RUN")
            self.assertEqual(result["files_deleted"], 0)
            self.assertIn(str(model_path.resolve()), result["artifacts"])

    def test_execute_sin_confirmacion_falla(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root, outputs_dir = self.make_project(temp_dir)
            with mock.patch.object(cleaner, "PROJECT_ROOT", project_root):
                with self.assertRaisesRegex(ValueError, "Confirmación inválida"):
                    cleaner.clean_training_outputs(
                        outputs_dir=outputs_dir,
                        execute=True,
                        confirm=None,
                        backup_before=False,
                        backup_dir=Path(temp_dir) / "backups",
                        keep_directory_structure=True,
                    )

    def test_confirmacion_incorrecta_falla(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root, outputs_dir = self.make_project(temp_dir)
            with mock.patch.object(cleaner, "PROJECT_ROOT", project_root):
                with self.assertRaisesRegex(ValueError, "Confirmación inválida"):
                    cleaner.clean_training_outputs(
                        outputs_dir=outputs_dir,
                        execute=True,
                        confirm="WRONG",
                        backup_before=False,
                        backup_dir=Path(temp_dir) / "backups",
                        keep_directory_structure=True,
                    )

    def test_outputs_dir_peligroso_falla(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root, _ = self.make_project(temp_dir)
            with mock.patch.object(cleaner, "PROJECT_ROOT", project_root):
                with self.assertRaisesRegex(ValueError, "raíz del proyecto"):
                    cleaner.validate_outputs_dir(project_root)

    def test_collect_training_artifacts_detecta_extensiones(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root, outputs_dir = self.make_project(temp_dir)
            paths = [
                outputs_dir / "custom_cnn" / "best_model.keras",
                outputs_dir / "custom_cnn" / "metrics.json",
                outputs_dir / "custom_cnn" / "predictions.csv",
                outputs_dir / "cnn_features_svm" / "svm_rbf.joblib",
                outputs_dir / "explainability" / "gradcam" / "case.png",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("artifact", encoding="utf-8")

            with mock.patch.object(cleaner, "PROJECT_ROOT", project_root):
                artifacts = cleaner.collect_training_artifacts(
                    outputs_dir,
                    cleaner.default_options(),
                )

            artifact_set = {path.resolve() for path in artifacts if path.is_file()}
            for path in paths:
                self.assertIn(path.resolve(), artifact_set)

    def test_recreate_outputs_structure_crea_carpetas(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            _, outputs_dir = self.make_project(temp_dir)

            cleaner.recreate_outputs_structure(outputs_dir)

            for relative_dir in cleaner.BASE_STRUCTURE:
                directory = outputs_dir / relative_dir
                self.assertTrue(directory.is_dir())
                self.assertTrue((directory / ".gitkeep").exists())

    def test_no_elimina_archivos_fuera_de_outputs_por_symlink(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root, outputs_dir = self.make_project(temp_dir)
            target = Path(temp_dir) / "outside.txt"
            target.write_text("do not delete", encoding="utf-8")
            symlink_path = outputs_dir / "custom_cnn" / "outside.csv"
            symlink_path.parent.mkdir(parents=True)
            symlink_path.symlink_to(target)

            with mock.patch.object(cleaner, "PROJECT_ROOT", project_root):
                result = cleaner.clean_training_outputs(
                    outputs_dir=outputs_dir,
                    execute=True,
                    confirm="DELETE_OUTPUTS",
                    backup_before=False,
                    backup_dir=Path(temp_dir) / "backups",
                    keep_directory_structure=True,
                )

            self.assertTrue(target.exists())
            self.assertEqual(target.read_text(encoding="utf-8"), "do not delete")
            self.assertNotIn(str(symlink_path), result["artifacts"])


if __name__ == "__main__":
    unittest.main()
