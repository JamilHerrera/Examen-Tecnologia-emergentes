import unittest
from unittest.mock import patch

import pandas as pd

from etl.audit import DataQualityMetrics
from etl.extract import DataExtractor
from etl.load import StagingLoader, load_phase
from etl.transform import DataCleaner


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


class AtomicCursor:
    def __init__(self, connection):
        self.connection = connection
        self.fast_executemany = False

    def execute(self, query, *parameters):
        self.connection.statements.append(query)

    def setinputsizes(self, sizes):
        self.connection.input_sizes = sizes

    def executemany(self, query, rows):
        if self.connection.fail_inserts:
            raise ValueError("simulated batch insert failure")
        self.connection.inserted_rows += len(rows)

    def close(self):
        pass


class AtomicConnection:
    def __init__(self, fail_inserts=False):
        self.fail_inserts = fail_inserts
        self.statements = []
        self.inserted_rows = 0
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return AtomicCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class AtomicConnector:
    def __init__(self, fail_inserts=False):
        self.connection = AtomicConnection(fail_inserts)


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

    def test_load_phase_fails_when_atomic_load_metadata_is_missing(self):
        rows = pd.DataFrame({"Value": ["loaded", "reject"]})

        succeeded = load_phase({"Example": rows}, {"Example": rows}, FakeConnector())

        self.assertFalse(succeeded)


class AtomicStagingLoadTests(unittest.TestCase):
    def setUp(self):
        self.extracted = {
            "Sales_Orders": pd.DataFrame({"OrderID": [1, 2], "Description": ["a", "b"]})
        }
        self.cleaned = {"Sales_Orders": self.extracted["Sales_Orders"].copy()}
        self.metadata = {
            "Sales_Orders": {
                "source_table": "Sales.Orders",
                "key_column": "OrderID",
                "mode": "full",
                "row_count": 2,
                "watermark_column": "LastEditedWhen",
            }
        }

    def test_load_phase_uses_atomic_loader_and_reports_insert_counts(self):
        connector = AtomicConnector()
        stats = {}

        succeeded = load_phase(
            self.extracted,
            self.cleaned,
            connector,
            mode="full",
            run_id=7,
            metadata=self.metadata,
            stats_out=stats,
        )

        self.assertTrue(succeeded)
        self.assertEqual(connector.connection.commits, 1)
        self.assertEqual(connector.connection.rollbacks, 0)
        self.assertEqual(connector.connection.inserted_rows, 4)
        self.assertEqual(stats[("Sales.Orders", "staging_raw")]["inserted"], 2)
        self.assertEqual(stats[("Sales.Orders", "staging_clean")]["inserted"], 2)

    def test_batch_failure_rolls_back_the_atomic_load(self):
        connector = AtomicConnector(fail_inserts=True)

        succeeded = load_phase(
            self.extracted,
            self.cleaned,
            connector,
            mode="full",
            run_id=7,
            metadata=self.metadata,
        )

        self.assertFalse(succeeded)
        self.assertEqual(connector.connection.commits, 0)
        self.assertEqual(connector.connection.rollbacks, 1)


class IncrementalExtractionTests(unittest.TestCase):
    @patch("etl.extract.SOURCE_TABLES", ["Sales.Orders"])
    def test_empty_incremental_delta_is_valid(self):
        extractor = DataExtractor(None)
        extractor.extracted_data["Sales_Orders"] = pd.DataFrame(columns=["OrderID"])
        extractor.extraction_metadata["Sales_Orders"] = {
            "source_table": "Sales.Orders",
            "mode": "incremental",
        }

        self.assertTrue(extractor.validate_extraction())

    @patch("etl.extract.SOURCE_TABLES", ["Sales.Orders"])
    def test_empty_full_extract_is_invalid(self):
        extractor = DataExtractor(None)
        extractor.extracted_data["Sales_Orders"] = pd.DataFrame(columns=["OrderID"])
        extractor.extraction_metadata["Sales_Orders"] = {
            "source_table": "Sales.Orders",
            "mode": "full",
        }

        self.assertFalse(extractor.validate_extraction())

    def test_catalogue_rejects_use_the_source_object_name(self):
        cleaner = DataCleaner()
        frame = pd.DataFrame({"CustomerCategoryID": [4, 4], "Name": ["first", "duplicate"]})

        cleaned = cleaner.clean_categorical_data(frame, "Sales_CustomerCategories")

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaner.rejected_rows[0]["source_table"], "Sales.CustomerCategories")
        self.assertEqual(cleaner.rejected_rows[0]["business_key"], "4")


if __name__ == "__main__":
    unittest.main()
