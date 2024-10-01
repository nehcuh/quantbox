import unittest
import datetime
import time
import pandas as pd
from quantbox.util.tools import util_make_date_stamp, util_to_json_from_pandas

class TestUtilFunctions(unittest.TestCase):
    def test_util_make_date_stamp(self):
        # Test with int input
        date_stamp = util_make_date_stamp(19901203)
        expected_stamp = time.mktime(time.strptime("1990-12-03", "%Y-%m-%d"))
        self.assertEqual(date_stamp, expected_stamp)

        # Test with str input
        date_stamp = util_make_date_stamp("2002-09-23")
        expected_stamp = time.mktime(time.strptime("2002-09-23", "%Y-%m-%d"))
        self.assertEqual(date_stamp, expected_stamp)

        # Test with datetime.date input
        date_stamp = util_make_date_stamp(datetime.date(2000, 1, 1))
        expected_stamp = time.mktime(time.strptime("2000-01-01", "%Y-%m-%d"))
        self.assertEqual(date_stamp, expected_stamp)

        # Test with None input
        today = datetime.date.today().strftime("%Y-%m-%d")
        date_stamp = util_make_date_stamp(None)
        expected_stamp = time.mktime(time.strptime(today, "%Y-%m-%d"))
        self.assertEqual(date_stamp, expected_stamp)

    def test_util_to_json_from_pandas(self):
        # Create a sample DataFrame
        df = pd.DataFrame({
            "id": [1, 2, 3],
            "date": [pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03")],
            "value": [10, 20, 30]
        })

        # Test conversion to JSON
        json_data = util_to_json_from_pandas(df)
        expected_json = [
            {"id": 1, "date": "2020-01-01", "value": 10},
            {"id": 2, "date": "2020-01-02", "value": 20},
            {"id": 3, "date": "2020-01-03", "value": 30},
        ]
        self.assertEqual(json_data, expected_json)

        # Test with additional columns
        df["datetime"] = pd.Timestamp("2020-01-01 12:00:00")
        json_data = util_to_json_from_pandas(df)
        expected_json = [
            {"id": 1, "date": "2020-01-01", "value": 10, "datetime": "2020-01-01 12:00:00"},
            {"id": 2, "date": "2020-01-02", "value": 20, "datetime": "2020-01-01 12:00:00"},
            {"id": 3, "date": "2020-01-03", "value": 30, "datetime": "2020-01-01 12:00:00"},
        ]
        self.assertEqual(json_data, expected_json)

if __name__ == "__main__":
    unittest.main()
