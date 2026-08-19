"""RAG 分块器纯函数测试。"""

import unittest

from insight_agent.rag.chunker import split_markdown


class TestChunker(unittest.TestCase):
    def test_split_by_sections(self):
        text = "# 标题A\n内容A\n\n# 标题B\n内容B"
        chunks = split_markdown(text, max_chars=15, overlap=0)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertIn("内容A", chunks[0])
        self.assertIn("内容B", chunks[1])

    def test_overlap_carried(self):
        text = "# A\n" + "x" * 50 + "\n# B\n" + "y" * 50
        chunks = split_markdown(text, max_chars=60, overlap=10)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertIn("xxx", chunks[1])

    def test_single_short_text(self):
        chunks = split_markdown("只有一句话")
        self.assertEqual(chunks, ["只有一句话"])


if __name__ == "__main__":
    unittest.main()
