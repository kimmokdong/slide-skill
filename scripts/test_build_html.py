import json
import re
import unittest
from pathlib import Path

from build_html import (
    load_theme,
    normalize_pages,
    normalize_slide_data,
    render_slide,
    render_worksheet_block,
    validate_pages,
)
from dev_server import apply_text_edits
from init_lesson_project import build_plan


class BuildHtmlContractTest(unittest.TestCase):
    def test_screen_autofit_minimum_never_drops_below_18px(self):
        css_path = Path(__file__).resolve().parents[1] / 'templates' / 'includes' / 'styles' / 'layouts.css'
        css = css_path.read_text(encoding='utf-8')
        minimums = [float(value) for value in re.findall(r'--autofit-min:\s*([0-9.]+)', css)]

        self.assertTrue(minimums)
        self.assertGreaterEqual(min(minimums), 18)

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

    def test_nested_template_conditionals_render_without_tokens(self):
        html = render_slide({
            'layout': 'tutorial',
            'TITLE': '첫 화면 만들기',
            'STEPPER_ITEMS': [{'label': '설계', 'state': 'active'}],
            'BULLET_ITEMS': ['핵심 행동을 고릅니다.'],
        })

        self.assertNotIn('{{#if', html)
        self.assertNotIn('{{/if}}', html)
        self.assertIn('stepper-container', html)

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

    def test_legacy_activity_package_builds_one_interactive_slide(self):
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
            ['activity', None, None],
        )
        self.assertEqual([page.get('page_type') for page in pages[:3]], ['slide', 'worksheet', 'answer_key'])

    def test_initializer_writes_one_canonical_activity(self):
        plan = build_plan({'topic': '안전', 'title': '안전 수업', 'activity_title': '안전 OX'})
        layouts = [page.get('layout') for page in plan['pages']]

        self.assertNotIn('activity_packages', plan)
        self.assertEqual(layouts[2], 'activity')
        self.assertNotIn('activity_prompt', layouts)
        self.assertNotIn('ox_reveal', layouts)
        self.assertEqual(json.dumps(plan, ensure_ascii=False).count('"block_type": "ox_check"'), 1)

    def test_activity_reference_resolves_for_all_outputs(self):
        plan = {
            'activities': [{
                'id': 'activity_1',
                'title': '안전 OX',
                'worksheet_block': {
                    'block_type': 'ox_check',
                    'title': '안전 확인',
                    'items': [{'statement': '안전하다', 'answer': 'O'}],
                },
            }],
            'pages': [
                {'page_type': 'slide', 'layout': 'activity', 'ACTIVITY_REF': 'activity_1'},
                {'page_type': 'worksheet', 'ACTIVITY_REFS': ['activity_1']},
                {'page_type': 'answer_key', 'ACTIVITY_REFS': ['activity_1']},
            ],
        }

        pages = normalize_pages(plan)
        normalized = normalize_slide_data(pages[0])
        html = render_slide(pages[0])

        self.assertEqual(normalized['layout'], 'ox_reveal')
        self.assertEqual(pages[1]['blocks'][0]['items'][0]['answer'], 'O')
        self.assertEqual(pages[2]['blocks'][0]['items'][0]['answer'], 'O')
        self.assertIn('data-edit-id="$root.activities[0].worksheet_block.items[0].statement"', html)
        self.assertIn('ox-reveal-answer fragment', html)

    def test_unknown_activity_reference_fails(self):
        with self.assertRaisesRegex(ValueError, '존재하지 않는 ACTIVITY_REF'):
            normalize_pages({
                'activities': [{
                    'id': 'activity_1',
                    'worksheet_block': {'block_type': 'ox_check', 'items': []},
                }],
                'pages': [{'page_type': 'slide', 'layout': 'activity', 'ACTIVITY_REF': 'missing'}],
            })

    def test_answer_key_requires_same_activity_id(self):
        block = {
            'block_type': 'matching_lines',
            'title': '선 잇기',
            'pairs': [{'left': '가', 'right': 'A'}],
        }
        with self.assertRaisesRegex(ValueError, '교사용 정답지에 활동 activity_2가 누락'):
            normalize_pages({
                'activities': [
                    {'id': 'activity_1', 'worksheet_block': block},
                    {'id': 'activity_2', 'worksheet_block': block},
                ],
                'pages': [
                    {'page_type': 'slide', 'layout': 'activity', 'ACTIVITY_REF': 'activity_1'},
                    {'page_type': 'slide', 'layout': 'activity', 'ACTIVITY_REF': 'activity_2'},
                    {'page_type': 'worksheet', 'ACTIVITY_REFS': ['activity_1', 'activity_2']},
                    {'page_type': 'answer_key', 'ACTIVITY_REFS': ['activity_1']},
                ],
            })

    def test_matching_uses_same_order_on_slide_and_worksheet(self):
        plan = {
            'activities': [{
                'id': 'match_1',
                'worksheet_block': {
                    'block_type': 'matching_lines',
                    'title': '선 잇기',
                    'pairs': [
                        {'left': '가', 'right': 'A'},
                        {'left': '나', 'right': 'B'},
                        {'left': '다', 'right': 'C'},
                    ],
                },
            }],
            'pages': [
                {'page_type': 'slide', 'layout': 'activity', 'ACTIVITY_REF': 'match_1'},
                {'page_type': 'worksheet', 'ACTIVITY_REFS': ['match_1']},
            ],
        }
        pages = normalize_pages(plan)
        slide_html = render_slide(pages[0])
        worksheet_html = render_worksheet_block(pages[1]['blocks'][0], 0, 1)

        pattern = r'class="match-right"[^>]*>([^<]+)</div>'
        self.assertEqual(re.findall(pattern, slide_html), re.findall(pattern, worksheet_html))

    def test_table_activity_reveals_only_marked_cells(self):
        html = render_slide({
            'layout': 'activity',
            'WORKSHEET_BLOCK': {
                'block_type': 'table_fill',
                'title': '표 채우기',
                'headers': ['항목', '설명', '정답'],
                'rows': [[
                    {'text': 'A'},
                    {'text': '계속 보임'},
                    {'text': '클릭 공개', 'is_blank': True},
                ]],
            },
        })

        self.assertEqual(html.count('pop-glow-reveal'), 1)
        self.assertIn('>계속 보임</td>', html)

    def test_video_hook_keeps_prompt_optional_and_editable(self):
        html = render_slide({
            'layout': 'video_hook',
            'TITLE': '희귀 동물 영상',
            'EMBED_URL': 'https://www.youtube.com/embed/abcdefghijk',
            'PURPOSE': '영상에서 특징을 찾아봅시다.',
        })

        self.assertIn('video-layout-body', html)
        self.assertIn('data-edit-id="PURPOSE"', html)
        self.assertIn('referrerpolicy="strict-origin-when-cross-origin"', html)
        self.assertNotIn('video-student-task', html)

    def test_activity_reveals_cloze_words_and_uses_merged_ox_answer_panel(self):
        cloze_html = render_slide({
            'layout': 'activity',
            'WORKSHEET_BLOCK': {
                'block_type': 'cloze_word_bank',
                'word_bank': ['정답'],
                'sentences': [{'text': '빈칸 [정답]', 'answer': '정답'}],
            },
        })
        ox_html = render_slide({
            'layout': 'activity',
            'WORKSHEET_BLOCK': {
                'block_type': 'ox_check',
                'items': [{'statement': '문장', 'answer': 'O', 'explanation': '해설'}],
            },
        })

        self.assertIn('js-cloze-word', cloze_html)
        self.assertIn('js-cloze-target', cloze_html)
        self.assertIn('class="ox-reveal-copy"', ox_html)
        self.assertIn('class="ox-reveal-answer fragment"', ox_html)

    def test_fullbleed_image_reveal_is_optional(self):
        html = render_slide({
            'layout': 'fullbleed',
            'TITLE': '지도 관찰',
            'IMAGE_SRC': 'images/map.png',
            'IMAGE_REVEAL': True,
        })

        self.assertIn('fullbleed-click-reveal', html)
        self.assertIn('aria-label="이미지 전체 보기"', html)

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
