import unittest

import pandas as pd

from etl.audit import DataQualityMetrics
from etl.load import StagingLoader, load_phase


class FakeCursor:
    def execute(self, query, parameters=None):
        if query.startswith("INSERT INTO") and parameters[0] == "reject":
            raise ValueError("row rejected by test cursor")

    def fetchone(self):
        return ("existing-schema",)

    def close(self):
        pass


class FakeConnection:
    def cursor(self):
        return FakeCursor()

    def commit(self):
        pass

    def rollback(self):
        pass


class FakeConnector:
    def __init__(self):
        self.connection = FakeConnection()


class QualityMetricTests(unittest.TestCase):
    def test_consistency_is_unmeasured_and_excluded_from_overall_score(self):
        df = pd.DataFrame({"ID": [1, 2], "Name": ["first", None]})

        metrics = DataQualityMetrics.quality_report({"Example": df})["Example"]

        measured_scores = [
            metrics["completeness_score"],
            metrics["uniqueness_score"],
            metrics["validity_score"],
        ]
        self.assertIsNone(metrics["consistency_score"])
        self.assertEqual(metrics["overall_quality_score"], sum(measured_scores) / 3)


class StagingLoaderTests(unittest.TestCase):
    def test_successful_loads_report_expected_and_inserted_rows(self):
        rows = pd.DataFrame({"Value": ["first", "second"]})
        load_methods = [
            ("load_to_staging_raw", "Example", "Example"),
            ("load_to_staging_clean", "Example", "Example_clean"),
        ]

        for method_name, table_name, stats_key in load_methods:
            with self.subTest(layer=method_name):
                loader = StagingLoader(FakeConnector())

                succeeded = getattr(loader, method_name)({table_name: rows})

                self.assertTrue(succeeded)
                self.assertEqual(loader.load_stats[stats_key]["expected_rows"], 2)
                self.assertEqual(loader.load_stats[stats_key]["rows"], 2)
                self.assertEqual(loader.load_stats[stats_key]["failed_rows"], 0)
                self.assertTrue(loader.load_stats[stats_key]["success"])

    def test_row_insert_errors_fail_both_staging_loads_with_counts(self):
        rows = pd.DataFrame({"Value": ["loaded", "reject", "loaded"]})
        load_methods = [
            ("load_to_staging_raw", "Example", "Example"),
            ("load_to_staging_clean", "Example", "Example_clean"),
        ]

        for method_name, table_name, stats_key in load_methods:
            with self.subTest(layer=method_name):
                loader = StagingLoader(FakeConnector())

                succeeded = getattr(loader, method_name)({table_name: rows})

                self.assertFalse(succeeded)
                self.assertEqual(loader.load_stats[stats_key]["expected_rows"], 3)
                self.assertEqual(loader.load_stats[stats_key]["rows"], 2)
                self.assertEqual(loader.load_stats[stats_key]["failed_rows"], 1)
                self.assertFalse(loader.load_stats[stats_key]["success"])

    def test_load_phase_fails_when_a_row_insert_fails(self):
        rows = pd.DataFrame({"Value": ["loaded", "reject"]})

        succeeded = load_phase({"Example": rows}, {"Example": rows}, FakeConnector())

        self.assertFalse(succeeded)


if __name__ == "__main__":
    unittest.main()
