"""V4 experiment parity and chronological memory tests; no final IDs generated."""
import copy
import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from generate import generate_patient
from train_v3 import trajectory_features, FEATURES
from train_v4_experiment import fast_features, memory_features, dataset, SPLITS, ROUTINES


class V4FeatureTests(unittest.TestCase):
    def test_vectorized_features_match_existing_prefix_contract(self):
        for routine in ROUTINES:
            patient = generate_patient(2499, **routine['params'])
            cursors = [288, 426, 720, 1086]
            actual = fast_features(patient, cursors)
            expected = np.asarray([[trajectory_features(patient, cursor)[key] for key in FEATURES] for cursor in cursors])
            np.testing.assert_allclose(actual, expected, atol=1e-8, rtol=1e-10)

    def test_future_measurements_and_unresolved_residuals_cannot_change_current_inputs(self):
        patient = generate_patient(2498, variable_routine=True)
        grid = np.arange(288, 408, 6)
        before = fast_features(patient, grid)
        mutated = copy.deepcopy(patient)
        for row in mutated['series'][grid[9] + 1:]:
            row.update(glucose=305., hr=140., hrv=90., steps=1400, sleep=1)
        after = fast_features(mutated, grid[:10])
        np.testing.assert_allclose(before[:10], after, atol=1e-8, rtol=1e-10)
        g = before[:, FEATURES.index('glucose')]
        predictions = g[:, None] + np.asarray([2., 4., 6., 8.])[None, :]
        probability = 1 / (1 + np.exp(-(g - 150) / 20))
        groups = np.full(len(grid), 2498); regimes = np.zeros(len(grid), dtype=int)
        full = memory_features(before, predictions, probability, groups, regimes, grid)
        prefix = memory_features(before[:10], predictions[:10], probability[:10], groups[:10], regimes[:10], grid[:10])
        np.testing.assert_array_equal(full[:10], prefix)
        self.assertEqual(full[3, len(FEATURES) + 5], 0)
        self.assertEqual(full[4, len(FEATURES) + 5], 1)
        self.assertEqual(full[4, len(FEATURES) + 6], g[4] - predictions[0, -1])

    def test_final_identity_generation_requires_gate_and_splits_are_disjoint(self):
        for name, ids in SPLITS.items():
            for other, other_ids in SPLITS.items():
                if name != other:
                    self.assertFalse(set(ids) & set(other_ids))
        with self.assertRaisesRegex(RuntimeError, 'prohibited'):
            dataset('forbidden', [4000], ROUTINES)


if __name__ == '__main__':
    unittest.main()
