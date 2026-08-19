"""export_csv / wants_export 的单元测试（不依赖数据库）。unittest 风格，pytest 亦兼容。"""

import base64
import json
import unittest
from unittest import mock

from insight_agent.tools.export import EXPORT_KEYWORDS, export_csv, wants_export


class TestWantsExport(unittest.TestCase):
    def test_positive(self):
        for question in [
            "帮我导出4月订单数据",
            "下载上个月的销售报表",
            "把客户列表导出成CSV",
            "导出一个 Excel 文件",
            "export data as xlsx",
        ]:
            with self.subTest(question=question):
                self.assertTrue(wants_export(question))

    def test_negative(self):
        for question in [
            "4月订单总数是多少",
            "各区域销售额对比",
            "帮我看看数据",
        ]:
            with self.subTest(question=question):
                self.assertFalse(wants_export(question))


class TestExportCsv(unittest.TestCase):
    def test_export_content(self):
        with mock.patch(
            "insight_agent.tools.export.fetch_rows",
            return_value=(["region", "total"], [["华东", 100.5], ["华南", 200.25]]),
        ):
            payload = json.loads(export_csv("SELECT region, total FROM t", user_id="1"))

        self.assertEqual(payload["filename"], "insight-export.csv")
        self.assertEqual(payload["mime"], "text/csv")
        self.assertEqual(payload["rowCount"], 2)

        decoded = base64.b64decode(payload["contentBase64"]).decode("utf-8")
        self.assertTrue(decoded.startswith("region,total"))
        self.assertIn("华东,100.5", decoded)
        self.assertIn("华南,200.25", decoded)

    def test_export_empty(self):
        with mock.patch(
            "insight_agent.tools.export.fetch_rows",
            return_value=(["a"], []),
        ):
            payload = json.loads(export_csv("SELECT a FROM t"))
        self.assertEqual(payload["rowCount"], 0)
        self.assertEqual(base64.b64decode(payload["contentBase64"]).decode("utf-8"), "a\r\n")

    def test_export_passes_user_id(self):
        captured = {}

        def fake_fetch_rows(sql, user_id=""):
            captured["user_id"] = user_id
            return (["a"], [])

        with mock.patch("insight_agent.tools.export.fetch_rows", side_effect=fake_fetch_rows):
            export_csv("SELECT a FROM dataset_1", user_id="7")
        self.assertEqual(captured["user_id"], "7")


if __name__ == "__main__":
    unittest.main()
