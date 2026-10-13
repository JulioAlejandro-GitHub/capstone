"""Offline tests; no DB connection and no dataset writes."""
import hashlib,io,unittest
from PIL import Image
from guards import require_read_only_select
from inspect_images import pixel_info,filename_patient,candidate

class AuditTests(unittest.TestCase):
    def test_patient_names_preserve_significant_suffixes(self) -> None:
        self.assertEqual(filename_patient('C47P8thin_Original_Motic_IMG_20150714_093512_cell_1.png'),'C47P8thin_Original_Motic')
        self.assertEqual(filename_patient('C72P33_ThinF_IMG_20150815_1_cell_3.png'),'C72P33_ThinF')
        self.assertIsNone(filename_patient('000001_uninfected.png'))

    def test_candidate_is_not_clinical_verification(self) -> None:
        self.assertEqual(candidate('228C86P47ThinF'),'C86P47ThinF')
        self.assertIsNone(candidate('C86P47ThinF'))
        self.assertIsNone(candidate('228anything'))
        self.assertNotEqual(candidate('146C47P8thin_Original_Motic'),candidate('148C47P8thinOriginalOlympusCX21'))

    def test_canonical_pixel_hash_ignores_encoding(self) -> None:
        img=Image.new('RGB',(3,2),(12,34,56));a=io.BytesIO();b=io.BytesIO()
        img.save(a,format='PNG',compress_level=0);img.save(b,format='PNG',compress_level=9)
        self.assertNotEqual(a.getvalue(),b.getvalue())
        self.assertEqual(pixel_info(a.getvalue()),pixel_info(b.getvalue()))
        self.assertEqual(pixel_info(a.getvalue()),(3,2,hashlib.sha256(bytes([12,34,56])*6).hexdigest()))

    def test_dimensions_are_part_of_comparison(self) -> None:
        a=io.BytesIO();b=io.BytesIO()
        Image.new('RGB',(3,2)).save(a,format='PNG');Image.new('RGB',(2,3)).save(b,format='PNG')
        self.assertEqual(pixel_info(a.getvalue())[2],pixel_info(b.getvalue())[2])
        self.assertNotEqual(pixel_info(a.getvalue()),pixel_info(b.getvalue()))

    def test_write_guard(self) -> None:
        require_read_only_select('SELECT id FROM dataset_versions WHERE id=:id')
        for sql in ['UPDATE datasets SET name=1','SELECT 1; DELETE FROM datasets','SELECT * INTO x FROM datasets','WITH x AS (DELETE FROM datasets RETURNING *) SELECT * FROM x','SELECT * FROM datasets FOR UPDATE','SELECT 1 -- anything','CALL ingest()']:
            with self.subTest(sql=sql),self.assertRaises(ValueError):require_read_only_select(sql)

if __name__=='__main__':unittest.main()
