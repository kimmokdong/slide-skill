import unittest

from build_html import load_theme, normalize_pages, normalize_slide_data, render_slide, validate_pages
from dev_server import apply_text_edits
from init_lesson_project import build_plan


class BuildHtmlContractTest(unittest.TestCase):
    def test_quiz_correct_flag_sets_answer_index(self):
        html = render_slide({
            'layout': 'quiz',
            'TITLE': '퀴즈',
            'QUESTION': '정답은?',
            'QUIZ_OPTIONS': [
                {'text': '오답', 'correct': False},
                {'text': '정답', 'correct': True},
            ],
        })

        self.assertIn('checkQuizAnswer(this, false)', html)
        self.assertIn('checkQuizAnswer(this, true)', html)
        self.assertLess(html.index('false)'), html.index('true)'))

    def test_legacy_aliases_keep_content(self):
        data = normalize_slide_data({
            'layout': 'ox_reveal',
            'TITLE': '정답',
            'BOTTOM_TAKEAWAY_HTML': '핵심 문장',
            'speaker_notes': '교사 메모',
            'OX_REVEAL_ITEMS': [{'statement': '문장', 'answer': 'O', 'reason': '이유'}],
        })

        self.assertEqual(data['BOTTOM_TAKEAWAY'], '핵심 문장')
        self.assertEqual(data['SPEAKER_NOTES'], '교사 메모')
        self.assertEqual(data['ITEMS'][0]['reason'], '이유')

    def test_quiz_without_answer_fails_gate(self):
        with self.assertRaisesRegex(ValueError, '정답 1개 필요'):
            validate_pages([{
                'page_type': 'slide',
                'layout': 'quiz',
                'TITLE': '퀴즈',
                'QUESTION': '정답은?',
                'QUIZ_OPTIONS': ['A', 'B'],
            }])

    def test_activity_package_includes_student_prompt(self):
        pages = normalize_pages({'activity_packages': [{
            'title': '안전 OX',
            'worksheet_block': {
                'block_type': 'ox_check',
                'title': '문항',
                'items': [{'statement': '안전하다', 'answer': 'O'}],
            },
        }]})

        self.assertEqual(
            [page.get('layout') for page in pages[:3]],
            ['activity_instruction', 'activity_prompt', 'ox_reveal'],
        )

    def test_initializer_writes_explicit_activity_prompt(self):
        plan = build_plan({'topic': '안전', 'title': '안전 수업', 'activity_title': '안전 OX'})
        layouts = [page.get('layout') for page in plan['pages']]

        self.assertNotIn('activity_packages', plan)
        self.assertEqual(
            layouts[2:5],
            ['activity_instruction', 'activity_prompt', 'ox_reveal'],
        )

    def test_direct_edits_prefer_pages_over_legacy_slides(self):
        plan = {
            'pages': [{'page_type': 'slide', 'layout': 'title', 'TITLE': '원래 제목'}],
            'slides': [{'layout': 'title', 'TITLE': '레거시 제목'}],
        }

        apply_text_edits(plan, [{'slideIndex': 0, 'editId': 'TITLE', 'value': '수정 제목'}], [])

        self.assertEqual(plan['pages'][0]['TITLE'], '수정 제목')
        self.assertEqual(plan['slides'][0]['TITLE'], '레거시 제목')

    def test_clean_school_theme_exists(self):
        self.assertIn('meta-theme-style', load_theme('clean_school'))

    def test_cloze_reveal_requires_word_bank_sentences(self):
        with self.assertRaisesRegex(ValueError, 'WORD_BANK'):
            validate_pages([{
                'page_type': 'slide',
                'layout': 'cloze_reveal',
                'TITLE': '빈칸',
                'ITEMS': [{'text': '빈칸 [정답]', 'answer': '정답'}],
            }])

    def test_answer_key_requires_matching_block(self):
        with self.assertRaisesRegex(ValueError, 'matching_lines 문항이 1개 누락'):
            validate_pages([
                {
                    'page_type': 'worksheet',
                    'BLOCKS': [{'block_type': 'matching_lines', 'pairs': []}],
                },
                {
                    'page_type': 'answer_key',
                    'BLOCKS': [],
                },
            ])


if __name__ == '__main__':
    unittest.main()
