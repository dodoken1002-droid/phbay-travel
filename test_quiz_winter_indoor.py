import datetime
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parent


class QuizWinterIndoorTests(unittest.TestCase):
    """內海冬季暫停預約期間，行程診斷改推冬季室內手作，3/1 起自動恢復推薦內海。"""

    def setUp(self):
        self.script = (ROOT / 'script.js').read_text(encoding='utf-8')
        self.results = self.script[self.script.index('const QUIZ_RESULTS'):
                                   self.script.index('/* ── 封存：追風音樂節')]

    def test_indoor_result_lists_the_three_experiences_without_made_up_price(self):
        block = re.search(r'  indoor: \{(.*?)\n  \},', self.results, re.S).group(1)
        for text in ('博藤基地', '蚵殼', '小烏龜', '南寮社區', '磨豆漿', '海沙炒花生'):
            self.assertIn(text, block)
        self.assertIn("price:'專人報價'", block)
        self.assertNotIn("url:", block)          # 沒有獨立商品頁，走諮詢表單
        self.assertIn("interest:'其他'", block)  # 諮詢表單固定有「其他」選項

    def test_winter_swap_uses_the_same_reopen_date_as_neihai(self):
        reopen = re.search(r"const QUIZ_NEIHAI_REOPEN = '(\d{4}-\d{2}-\d{2})'", self.script).group(1)
        index = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertIn(f'data-open-from="{reopen}"', index)
        app = (ROOT / 'app.py').read_text(encoding='utf-8')
        end = re.search(r'NEIHAI_CLOSED_PERIODS = \(\s*\(date\([^)]*\), date\((\d+), (\d+), (\d+)\)', app)
        closed_until = datetime.date(*(int(x) for x in end.groups()))
        self.assertEqual(reopen, (closed_until + datetime.timedelta(days=1)).isoformat())
        self.assertIn("timeZone: 'Asia/Taipei'", self.script[self.script.index('function quizSeasonalResult'):])

    def test_result_and_shared_links_go_through_the_seasonal_swap(self):
        render = self.script[self.script.index('function renderQuizResult'):]
        self.assertIn('const best = quizSeasonalResult(', render[:600])
        totals = re.search(r'const totals = \{([^}]*)\}', render).group(1)
        self.assertNotIn('indoor', totals)  # 只在冬季替換時出現，不參與一般計分

    def test_contact_prefill_carries_the_note(self):
        self.assertIn("prefillTour('${r.tour.interest}','${r.tour.note || ''}')", self.script)
        self.assertIn("if (notes && note && !notes.value.trim()) notes.value = note;", self.script)

    def test_ai_note_accepts_indoor_without_place_names(self):
        app = (ROOT / 'app.py').read_text(encoding='utf-8')
        mapping = re.search(r'^_QUIZ_AI_RESULTS = \{(.*?)\}', app, re.S | re.M).group(1)
        label = re.search(r"'indoor': '([^']+)'", mapping).group(1)
        self.assertNotIn('博藤', label)  # AI 提示要求不可提店名
        self.assertNotIn('南寮', label)


if __name__ == '__main__':
    unittest.main()
