"""db.py 安全拦截逻辑测试（只测查询前的拦截路径，不连数据库）。"""

import unittest

from insight_agent.tools import db


class TestDbSafety(unittest.TestCase):
    def test_blocks_write_keywords(self):
        for sql in [
            "DELETE FROM orders",
            "UPDATE orders SET amount = 0",
            "DROP TABLE orders",
            "ALTER TABLE orders ADD COLUMN x int",
            "TRUNCATE orders",
            "INSERT INTO orders VALUES (1)",
            "create table evil (id int)",
        ]:
            with self.subTest(sql=sql):
                with self.assertRaises(PermissionError):
                    db.fetch_rows(sql)

    def test_blocks_multi_statement(self):
        with self.assertRaises(ValueError):
            db.fetch_rows("SELECT 1; SELECT 2")

    def test_query_database_returns_friendly_error(self):
        out = db.query_database("delete from orders")
        self.assertIn("只允许", out)
        out = db.query_database("SELECT 1; SELECT 2")
        self.assertIn("多条语句", out)


if __name__ == "__main__":
    unittest.main()
