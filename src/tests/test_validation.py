import sys
from pathlib import Path
import unittest

# Add src to path
SRC = Path(__file__).resolve().parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from validate import validate_prices, validate_features, validate_labels

class TestValidation(unittest.TestCase):
    def test_prices_empty(self):
        import pandas as pd
        errs, warns = validate_prices(pd.DataFrame())
        self.assertEqual(len(errs), 1)
        self.assertIn("EMPTY", errs[0])
    
    def test_prices_bad_isin(self):
        import pandas as pd
        df = pd.DataFrame({
            'date': ['2023-01-01'],
            'isin': ['BAD123'],
            'close': [100.0]
        })
        errs, warns = validate_prices(df)
        self.assertTrue(any("Bad ISIN" in e for e in errs))
    
    def test_prices_zero_close(self):
        import pandas as pd
        df = pd.DataFrame({
            'date': ['2023-01-01'] * 3,
            'isin': ['MA0000010001'] * 3,
            'close': [100.0, 0.0, 50.0],
            'open': [100.0, 0.0, 50.0],
            'high': [100.0, 0.0, 50.0],
            'low': [100.0, 0.0, 50.0]
        })
        errs, warns = validate_prices(df)
        self.assertTrue(any("zero" in e.lower() for e in errs))
    
    def test_prices_price_logic(self):
        import pandas as pd
        df = pd.DataFrame({
            'date': ['2023-01-01'],
            'isin': ['MA0000010001'],
            'close': [100.0],
            'open': [100.0],
            'high': [90.0],  # high < close, invalid
            'low': [110.0]   # low > close, invalid
        })
        errs, warns = validate_prices(df)
        self.assertTrue(any("Price logic" in e for e in errs))
    
    def test_features_extreme_return(self):
        import pandas as pd
        df = pd.DataFrame({
            'date': ['2023-01-01'],
            'isin': ['MA0000010001'],
            'close': [100.0],
            'return_': [0.5]  # 50% return, extreme
        })
        errs, warns = validate_features(df)
        self.assertTrue(any("Extreme" in w for w in warns))
    
    def test_labels_few_positives(self):
        import pandas as pd
        df = pd.DataFrame({
            'date': ['2023-01-01'] * 5,
            'isin': ['MA0000010001'] * 5,
            'return_': [0.01]*5,
            'forward_return': [0.01]*5,
            'label': [0]*5
        })
        errs, warns = validate_labels(df)
        self.assertTrue(any("Few positives" in w for w in warns))

if __name__ == '__main__':
    unittest.main()
