import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parent


class QuizFestivalArchiveTests(unittest.TestCase):
    """追風音樂節已結束：行程診斷的音樂節選項與結果封存，不可再被選到或算出。"""

    def setUp(self):
        script = (ROOT / 'script.js').read_text(encoding='utf-8')
        self.questions = script[script.index('const QUIZ_QUESTIONS'):script.index('const QUIZ_RESULTS')]
        self.results = script[script.index('const QUIZ_RESULTS'):script.index('/* ── 封存：追風音樂節')]
        self.archive = script[script.index('const QUIZ_ARCHIVED_FESTIVAL'):script.index('let quizAnswers')]
        self.render = script[script.index('function renderQuizResult'):]

    def test_festival_option_weights_and_result_are_inactive(self):
        self.assertNotIn('festival', self.questions)
        self.assertNotIn("text:'音樂節'", self.questions)
        self.assertNotIn('festival', self.results)
        totals = re.search(r'const totals = \{([^}]*)\}', self.render).group(1)
        self.assertNotIn('festival', totals)

    def test_archive_keeps_everything_needed_to_restore(self):
        self.assertIn("text:'音樂節'", self.archive)
        self.assertIn("type: '追風音樂節玩家 🎵'", self.archive)
        self.assertIn("url:'/preorder/festival'", self.archive)
        for answer in ('情侶 兩人', '一群朋友', '公司員旅 / 揪團', '3 天 2 夜'):
            self.assertIn(f"'{answer}'", self.archive)

    def test_every_question_still_has_four_options(self):
        blocks = re.findall(r'options: \[(.*?)\n    \]', self.questions, re.S)
        self.assertEqual([b.count('icon:') for b in blocks], [4, 4, 4, 4, 4])

    def test_ai_note_api_no_longer_accepts_festival(self):
        app = (ROOT / 'app.py').read_text(encoding='utf-8')
        mapping = re.search(r'^_QUIZ_AI_RESULTS = \{(.*?)\}', app, re.S | re.M).group(1)
        self.assertNotIn("'festival'", mapping)
        self.assertIn("'tides'", mapping)


if __name__ == '__main__':
    unittest.main()
