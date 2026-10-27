import os
import sqlite3
import tempfile
import unittest

import db, llm, safety


class SafetyTests(unittest.TestCase):
    def test_allows_select_and_adds_limit(self):
        self.assertTrue(safety.validate_sql("SELECT * FROM orders").endswith("LIMIT 200"))

    def test_allows_with(self):
        safety.validate_sql("WITH t AS (SELECT 1 AS x) SELECT x FROM t")

    def test_blocks_writes(self):
        for bad in ["DROP TABLE orders", "DELETE FROM orders", "UPDATE orders SET status='x'",
                    "SELECT 1; DROP TABLE orders", "INSERT INTO orders VALUES (1)",
                    "SELECT * FROM orders -- hi", "PRAGMA table_info(orders)", "ATTACH 'x.db' AS x"]:
            with self.assertRaises(safety.UnsafeSQL, msg=bad):
                safety.validate_sql(bad)

    def test_column_names_with_blocked_words_are_ok(self):
        safety.validate_sql("SELECT created_at, updated_at FROM t")

    def test_readonly_layer_blocks_even_if_text_check_is_bypassed(self):
        path = os.path.join(tempfile.mkdtemp(), "t.db")
        db.init_db(path)
        with self.assertRaises(sqlite3.Error):
            safety.run_readonly(path, "DELETE FROM orders")
        cols, rows = safety.run_readonly(path, "SELECT COUNT(*) AS n FROM orders")
        self.assertEqual(rows[0][0], 1500)


class DemoModeTests(unittest.TestCase):
    def test_demo_queries_run(self):
        path = os.path.join(tempfile.mkdtemp(), "t.db")
        db.init_db(path)
        os.environ.pop("GEMINI_API_KEY", None)
        for q in ["top products", "revenue by month", "orders by city", "revenue by category"]:
            out = llm.generate_sql(q, "")
            cols, rows = safety.run_readonly(path, safety.validate_sql(out["sql"]))
            self.assertTrue(rows, q)


if __name__ == "__main__":
    unittest.main()
