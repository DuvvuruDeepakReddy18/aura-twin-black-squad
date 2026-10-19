"""Cache-integrity checks without fitting models or generating final identities."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import train_v3 as training


class TrainingCacheTests(unittest.TestCase):
    def test_matching_cache_is_reused_but_changed_feature_contract_is_rejected(self):
        rows=6*70
        def fixture(*args,**kwargs):
            return {'x':np.zeros((rows,len(training.FEATURES))),
                    'y':np.zeros((rows,4)),'groups':np.full(rows,1),
                    'routines':np.repeat(np.arange(6),70),'retained':{}}
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(training,'WORK',Path(folder)),patch.object(training,'dataset',side_effect=fixture) as generate:
                initial=training.cached_dataset('unit',[1],12)
                repeated=training.cached_dataset('unit',[1],12)
                self.assertEqual(generate.call_count,1)
                np.testing.assert_array_equal(initial['x'],repeated['x'])
                with patch.object(training,'EXTRA_LAGS',training.EXTRA_LAGS+[55]):
                    with self.assertRaisesRegex(RuntimeError,'provenance'):
                        training.cached_dataset('unit',[1],12)


if __name__=='__main__':
    unittest.main()
