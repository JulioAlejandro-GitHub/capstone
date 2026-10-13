"""Synthetic ThinBloodSmearsPf Polygon Set trees mirroring the real layout."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


WIDTH, HEIGHT = 64, 48
CELL = "1-{n},{label},No_comment,Polygon,4,10,10,20,10,20,20,10,20"


def gt_text(labels: list[str], width: int = WIDTH, height: int = HEIGHT) -> str:
    rows = [CELL.format(n=index, label=label) for index, label in enumerate(labels, start=1)]
    return "\n".join([f"{len(labels)},{width},{height}", *rows])


def write_smear(root: Path, patient: str, stem: str, *, seed: int,
                labels: list[str] | None = None, image_dir: str = "Img") -> Path:
    patient_dir = root / "Polygon Set" / patient
    (patient_dir / image_dir).mkdir(parents=True, exist_ok=True)
    (patient_dir / "GT").mkdir(parents=True, exist_ok=True)
    image_path = patient_dir / image_dir / f"{stem}.jpg"
    Image.new("RGB", (WIDTH, HEIGHT), (seed % 256, (seed * 7) % 256, 90)).save(image_path)
    (patient_dir / "GT" / f"{stem}.txt").write_text(
        gt_text(labels or ["Uninfected", "Parasitized", "White_Blood_Cell"]), encoding="utf-8"
    )
    return image_path


def build_tree(root: Path, patients: dict[str, int] | None = None) -> Path:
    """Default: patient A with 3 smears, patient B with 2, plus a ReadMe and Thumbs.db."""
    patients = patients or {"201C1P1ThinF": 3, "202C2NThinF": 2}
    seed = 1
    for patient, count in patients.items():
        for index in range(count):
            write_smear(root, patient, f"IMG_{index:02d}", seed=seed)
            seed += 1
        (root / "Polygon Set" / patient / "Img" / "Thumbs.db").write_bytes(b"thumbs")
    (root / "ReadMe.pdf").write_bytes(b"synthetic readme")
    return root
