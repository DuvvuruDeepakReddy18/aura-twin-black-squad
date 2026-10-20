"""Importer safety tests with explicit tiny CSV fixtures, never demo data."""
import csv
from datetime import date
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('synthea_ingestion', ROOT / 'scripts/ingest_synthea.py')
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


class SyntheaIngestionTests(unittest.TestCase):
    def fixture(self, folder):
        path = Path(folder) / 'source.zip'
        tables = {
            'patients.csv': (['Id', 'BIRTHDATE', 'DEATHDATE', 'GENDER', 'FIRST', 'ADDRESS'],
                             [['source-a', '1990-06-01', '', 'F', 'DO-NOT-EXPORT', 'PRIVATE-FIXTURE'],
                              ['source-child', '2010-01-01', '', 'M', 'CHILD', 'PRIVATE-FIXTURE']]),
            'observations.csv': (['DATE', 'PATIENT', 'CODE', 'DESCRIPTION', 'VALUE', 'UNITS', 'TYPE'],
                                 [['2018-01-01T00:00:00Z', 'source-a', '4548-4', 'Fixture HbA1c', '5.2', '%', 'numeric'],
                                  ['2020-01-01T00:00:00Z', 'source-a', '4548-4', 'Future sentinel', '999', '%', 'numeric']]),
            'conditions.csv': (['START', 'STOP', 'PATIENT', 'CODE', 'DESCRIPTION'],
                               [['2017-01-01', '2018-01-01', 'source-a', 'fixture', 'Ended fixture condition']]),
            'medications.csv': (['START', 'STOP', 'PATIENT', 'CODE', 'DESCRIPTION'],
                                [['2018-01-01', '2021-01-01', 'source-a', 'fixture', 'Fixture medication'],
                                 ['2020-01-01', '', 'source-a', 'future', 'Future medication']]),
        }
        with zipfile.ZipFile(path, 'w') as archive:
            for name, (header, rows) in tables.items():
                text = io.StringIO(newline='')
                writer = csv.writer(text)
                writer.writerow(header)
                writer.writerows(rows)
                archive.writestr(name, text.getvalue())
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_snapshot_withholds_future_values_and_future_resolution(self):
        with tempfile.TemporaryDirectory() as folder:
            archive, digest = self.fixture(folder)
            payload, manifest, _ = ingest.build(archive, Path(folder) / 'out', date(2019, 1, 1), 1, digest)
            profile = payload['profiles'][0]
            self.assertEqual(profile['hba1c'], 5.2)
            self.assertEqual(len(profile['observations']), 1)
            self.assertEqual(len(profile['medications']), 1)
            self.assertIsNone(profile['medications'][0]['stop'])
            self.assertEqual(profile['medications'][0]['statusAtSnapshot'], 'active')
            self.assertEqual(profile['diagnoses'][0]['statusAtSnapshot'], 'ended')
            self.assertEqual(manifest['validation']['observations.csv']['afterSnapshotRows'], 1)

    def test_private_fields_absent_and_missing_labs_stay_null(self):
        with tempfile.TemporaryDirectory() as folder:
            archive, digest = self.fixture(folder)
            payload, manifest, assignment = ingest.build(archive, Path(folder) / 'out', date(2019, 1, 1), 1, digest)
            profile = payload['profiles'][0]
            self.assertIsNone(profile['bmi'])
            self.assertIsNone(profile['ldl'])
            self.assertIsNone(profile['geneticContext'])
            self.assertEqual(profile['age'], 28)
            self.assertEqual(manifest['selection']['exclusions']['under18AtSnapshot'], 1)
            published = json.dumps([payload, manifest, assignment])
            for private in ['DO-NOT-EXPORT', 'PRIVATE-FIXTURE', 'source-a', '1990-06-01']:
                self.assertNotIn(private, published)
            self.assertFalse(assignment['clinicalIdentityLinkage'])
            self.assertFalse(assignment['targetDriven'])

    def test_archive_mismatch_fails_before_publishing(self):
        with tempfile.TemporaryDirectory() as folder:
            archive, _ = self.fixture(folder)
            out = Path(folder) / 'out'
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                ingest.build(archive, out, date(2019, 1, 1), 1, '0' * 64)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
