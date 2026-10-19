"""Fast independent generator/feature checks; never fits or selects a model."""
import json
from pathlib import Path
import unittest

from generate import generate_patient
from train_robust import robust_features

ROOT = Path(__file__).resolve().parents[1]


class DataContractTests(unittest.TestCase):
    def test_default_generator_reproduces_archived_streams(self):
        archived = json.loads((ROOT/'data/baseline-v1/patients.json').read_text(encoding='utf-8'))
        for patient in archived:
            generated = generate_patient(int(patient['id'].split('-')[1])-1)
            self.assertEqual(generated['ehr'], patient['ehr'])
            self.assertEqual(generated['series'], patient['series'])

    def test_meal_changes_keep_identity_and_unrelated_streams_paired(self):
        original = generate_patient(9)
        changed = generate_patient(9, meal_shift_hours=4, meal_jitter_hours=1.5,
                                   day_shift_hours_sd=1.8, meal_skip_probability=.22)
        self.assertEqual(original['ehr'], changed['ehr'])
        for field in ['timestamp', 'steps', 'sleep', 'hrv']:
            self.assertEqual([row[field] for row in original['series']],
                             [row[field] for row in changed['series']], field)
        self.assertNotEqual([row['glucose'] for row in original['series']],
                            [row['glucose'] for row in changed['series']])

    def test_variable_sleep_does_not_turn_midnight_wrap_into_all_day_sleep(self):
        # Development identities only. Bedtime can cross midnight on changed routines.
        for identity in range(24):
            patient = generate_patient(identity, variable_routine=True)
            for day in range(4):
                sleeping = sum(row['sleep'] for row in patient['series'][day*288:(day+1)*288])
                self.assertGreater(sleeping, 0)
                self.assertLess(sleeping, 240, f'All-day sleep: identity {identity}, day {day}')

    def test_python_features_do_not_read_after_the_cutoff(self):
        patient = generate_patient(8, meal_jitter_hours=1.5, day_shift_hours_sd=2)
        cursor = 610
        features = robust_features(patient, cursor)
        prefix = {**patient, 'series': patient['series'][:cursor+1]}
        self.assertEqual(features, robust_features(prefix, cursor))
        self.assertEqual(features['priorDay120'], patient['series'][cursor-264]['glucose'])
        for row in patient['series'][cursor+1:]:
            row['glucose'] = None
            row['timestamp'] = 'invalid future'
        self.assertEqual(features, robust_features(patient, cursor))


if __name__ == '__main__':
    unittest.main()
