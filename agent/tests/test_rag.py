"""RAG 检索器纯函数测试：关键词切词、命中排序、RRF 融合（不连数据库）。"""

import unittest

from insight_agent.rag.retriever import _keyword_terms, _rank_by_terms, _rrf_merge


class TestKeywordTerms(unittest.TestCase):
    def test_chinese_bigrams(self):
        terms = _keyword_terms("订单状态")
        self.assertIn("订单", terms)
        self.assertIn("单状", terms)
        self.assertIn("状态", terms)

    def test_latin_tokens(self):
        terms = _keyword_terms("task:input")
        self.assertTrue(any("task" in t or "input" in t for t in terms))


class TestRankByTerms(unittest.TestCase):
    def test_ranks_by_hit_count(self):
        candidates = [
            (1, "a", "订单 订单 状态"),
            (2, "b", "订单"),
            (3, "c", "其他内容"),
        ]
        ranked = _rank_by_terms(candidates, ["订单", "状态"])
        # id=1 命中 2 个词排最前，id=2 命中 1 个，id=3 命中 0 被过滤
        self.assertEqual(ranked, [1, 2])

    def test_empty_candidates(self):
        self.assertEqual(_rank_by_terms([], ["x"]), [])


class TestRrfMerge(unittest.TestCase):
    def test_merge_two_rankings(self):
        merged = _rrf_merge([1, 2, 3], [2, 1, 4], top_k=3)
        # 1 和 2 在两路都出现，得分高于只出现一路的 3/4
        self.assertEqual(list(merged.keys()), [1, 2, 3])

    def test_single_ranking(self):
        merged = _rrf_merge([5, 6], [], top_k=2)
        self.assertEqual(list(merged.keys()), [5, 6])

    def test_top_k_limit(self):
        merged = _rrf_merge([1, 2, 3, 4], [], top_k=2)
        self.assertEqual(len(merged), 2)


if __name__ == "__main__":
    unittest.main()
