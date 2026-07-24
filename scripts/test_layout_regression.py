#!/usr/bin/env python3
"""전체 레이아웃을 고정 테마와 동적 글꼴 프리셋으로 렌더링해 QA한다."""

import argparse
import asyncio
import json
from copy import deepcopy
from pathlib import Path

from build_html import ACTIVITY_LAYOUT_BY_BLOCK, REQUIRED_LAYOUT_FIELDS, build_html
from capture_png import capture_pngs


ROOT = Path(__file__).resolve().parents[1]
FIXED_THEMES = sorted(path.stem.removeprefix('theme_') for path in (ROOT / 'templates' / 'themes').glob('theme_*.css'))
FONT_PRESETS = ('friendly', 'cyber', 'classic', 'editorial', 'chalkboard')


def activity(activity_id, block):
    return {'id': activity_id, 'title': block['title'], 'worksheet_block': block}


def representative_plan():
    images = sorted((ROOT / 'sample').glob('*.png'))
    if len(images) < 2:
        raise RuntimeError('회귀 테스트에는 sample PNG가 2개 이상 필요합니다.')
    image_a, image_b = (images[0].resolve().as_uri(), images[1].resolve().as_uri())

    activities = [
        activity('ox', {
            'block_type': 'ox_check', 'title': '안전 OX',
            'items': [
                {'statement': '공용 컴퓨터에서는 사용 후 로그아웃합니다.', 'answer': 'O', 'explanation': '계정을 보호할 수 있습니다.'},
                {'statement': '비밀번호는 친구와 공유해도 됩니다.', 'answer': 'X', 'explanation': '비밀번호는 본인만 알아야 합니다.'},
                {'statement': '출처가 분명하지 않은 링크는 바로 열지 않습니다.', 'answer': 'O', 'explanation': '보낸 사람과 주소를 먼저 확인합니다.'},
                {'statement': '친구 사진은 허락 없이 온라인에 올려도 됩니다.', 'answer': 'X', 'explanation': '사진을 올리기 전에 당사자의 동의를 받습니다.'},
            ],
        }),
        activity('cloze', {
            'block_type': 'cloze_word_bank', 'title': '핵심어 빈칸 채우기',
            'word_bank': ['검증', '설계'],
            'sentences': [
                {'text': '큰 흐름을 [설계]합니다.', 'answer': '설계'},
                {'text': 'AI가 만든 결과를 [검증]합니다.', 'answer': '검증'},
            ],
        }),
        activity('matching', {
            'block_type': 'matching_lines', 'title': '동물과 서식지 연결하기',
            'pairs': [
                {'left': '재규어', 'right': '아마존 열대우림'},
                {'left': '낙타', 'right': '뜨거운 사막'},
                {'left': '펭귄', 'right': '추운 남극'},
            ],
        }),
        activity('table', {
            'block_type': 'table_fill', 'title': '행동 기준표 완성하기',
            'headers': ['상황', '확인할 행동', '이유'],
            'rows': [[
                {'text': '정보를 찾았을 때'},
                {'text': '출처 확인', 'is_blank': True},
                {'text': '믿을 만한지 판단하기 위해'},
            ]],
        }),
        activity('short', {
            'block_type': 'short_answer', 'title': '한 문장으로 설명하기',
            'prompt': '설계자의 역할이 중요한 까닭은 무엇인가요?',
            'sample_answer': '서비스의 큰 흐름을 정하고 AI의 결과를 비판적으로 검증해야 하기 때문입니다.',
            'answer_lines': 2,
        }),
    ]

    stepper = [
        {'label': '문제 찾기', 'state': 'completed'},
        {'label': '화면 만들기', 'state': 'active'},
        {'label': '친구 검증', 'state': 'inactive'},
    ]
    pages = [
        {'page_type': 'slide', 'layout': 'hero', 'TITLE': '바이브코딩 첫걸음', 'SUBTITLE': '생각을 작동하는 화면으로 바꿉니다', 'BADGE': '초등 수업', 'PRESENTER': '현승쌤'},
        {'page_type': 'slide', 'layout': 'title', 'TITLE': '문제에서 해결까지', 'SUBTITLE': '오늘 배울 흐름을 살펴봅시다.'},
        {'page_type': 'slide', 'layout': 'split', 'TITLE': '설계자의 역할', 'BODY': '어떤 서비스를 만들지 큰 흐름을 설계하고, AI가 만든 결과를 비판적으로 검증합니다.', 'IMAGE_SRC': image_a},
        {'page_type': 'slide', 'layout': 'text_image', 'TITLE': '사용자 관찰하기', 'CONTENT': '말보다 행동을 관찰하면 실제로 불편한 지점을 더 정확히 찾을 수 있습니다.', 'IMAGE_SRC': image_b, 'CAPTION': '사용자의 행동에서 문제를 찾습니다.'},
        {'page_type': 'slide', 'layout': 'bullet', 'TITLE': '좋은 문제의 조건', 'BULLET_ITEMS': [
            {'icon': '1', 'text': '누가 불편한지 분명합니다.'},
            {'icon': '2', 'text': '언제 문제가 생기는지 보입니다.'},
            {'icon': '3', 'text': '해결 뒤의 변화를 확인할 수 있습니다.'},
        ], 'BOTTOM_TAKEAWAY': '문제가 선명하면 해결 방법도 선명해집니다.'},
        {'page_type': 'slide', 'layout': 'comparison', 'TITLE': '좋은 요청과 아쉬운 요청', 'LEFT_TITLE': '좋은 요청', 'LEFT_ITEMS': [
            {'title': '목표', 'desc': '누가 무엇을 하게 만들지 씁니다.'},
            {'title': '조건', 'desc': '필요한 자료와 제한을 알려 줍니다.'},
        ], 'RIGHT_TITLE': '아쉬운 요청', 'RIGHT_ITEMS': [
            {'title': '모호함', 'desc': '그냥 멋지게 만들어 달라고 합니다.'},
            {'title': '검증 없음', 'desc': '결과를 확인할 기준이 없습니다.'},
        ]},
        {'page_type': 'slide', 'layout': 'image_comparison', 'TITLE': '첫 화면 비교', 'LEFT_IMAGE_SRC': image_a, 'RIGHT_IMAGE_SRC': image_b, 'LEFT_DESC': '정보가 한곳에 몰린 화면', 'RIGHT_DESC': '핵심 행동이 선명한 화면'},
        {'page_type': 'slide', 'layout': 'timeline', 'TITLE': '아이디어가 서비스가 되는 과정', 'TIMELINE_ITEMS': [
            {'date': '1일', 'title': '관찰', 'desc': '사용자의 불편을 찾습니다.'},
            {'date': '2일', 'title': '설계', 'desc': '핵심 행동의 흐름을 정합니다.'},
            {'date': '3일', 'title': '구현', 'desc': '작동하는 첫 화면을 만듭니다.'},
            {'date': '4일', 'title': '검증', 'desc': '친구의 사용 모습을 관찰합니다.'},
        ]},
        {'page_type': 'slide', 'layout': 'quiz', 'TITLE': '어떤 요청이 더 좋을까요?', 'QUESTION': '사용자와 목표가 가장 분명한 요청을 고르세요.', 'QUIZ_OPTIONS': [
            {'text': '아무 앱이나 멋지게 만들어 줘'},
            {'text': '학생이 급식 메뉴를 날짜별로 확인하는 화면을 만들어 줘', 'correct': True},
            {'text': '요즘 인기 있는 기능을 모두 넣어 줘'},
            {'text': '색깔이 화려한 화면을 만들어 줘'},
        ]},
        {'page_type': 'slide', 'layout': 'quote', 'QUOTE_TEXT': '작게 만들고, 직접 써 보고, 더 나은 질문을 찾습니다.', 'QUOTE_SOURCE': '오늘의 개발 원칙'},
        {'page_type': 'slide', 'layout': 'diagram', 'TITLE': '서비스의 기본 흐름', 'DIAGRAM_SRC': image_a, 'DIAGRAM_CAPTION': '입력에서 결과 확인까지 한 방향으로 이어집니다.'},
        {'page_type': 'slide', 'layout': 'stats', 'TITLE': '사용자 검증 결과', 'STAT_ITEMS': [
            {'value': '80%', 'label': '첫 화면에서 핵심 행동을 찾은 비율'},
            {'value': '3회', 'label': '평균 수정 횟수'},
            {'value': '1분', 'label': '친구가 기능을 이해한 시간'},
        ]},
        {'page_type': 'slide', 'layout': 'summary', 'TITLE': '오늘 배운 세 가지', 'SUMMARY_ITEMS': [
            {'title': '문제', 'desc': '사용자의 실제 불편에서 시작합니다.'},
            {'title': '설계', 'desc': '핵심 행동의 순서를 먼저 정합니다.'},
            {'title': '검증', 'desc': '친구가 쓰는 모습을 보고 고칩니다.'},
        ], 'BOTTOM_TAKEAWAY': '코딩보다 먼저 문제와 흐름을 설계합니다.'},
        {'page_type': 'slide', 'layout': 'closing', 'TITLE': '이제 직접 만들어 봅시다', 'MESSAGE': '작은 문제 하나를 골라 첫 화면을 완성합니다.', 'BULLET_ITEMS': ['관찰하기', '만들기', '검증하기'], 'CTA': '오늘 바로 시작'},
        {'page_type': 'slide', 'layout': 'tutorial', 'TITLE': '첫 화면 구성하기', 'STEPPER_ITEMS': stepper, 'BULLET_ITEMS': [
            {'title': '핵심 행동 선택', 'desc': '사용자가 가장 먼저 할 행동을 고릅니다.'},
            {'title': '버튼 배치', 'desc': '그 행동을 바로 실행할 위치에 둡니다.'},
        ], 'TIP': '한 화면에는 핵심 행동 하나만 남깁니다.', 'WARNING': '설명 문장을 너무 많이 넣지 않습니다.', 'IMAGE_SRC': image_b},
        {'page_type': 'slide', 'layout': 'hands_on', 'TITLE': '첫 화면 직접 만들기', 'STEPPER_ITEMS': stepper, 'BULLET_ITEMS': [
            '가장 중요한 행동을 한 가지 고릅니다.',
            '그 행동을 실행할 버튼을 배치합니다.',
            '친구에게 보여 주고 불편을 찾습니다.',
        ], 'TIP': '완벽함보다 실제 작동을 먼저 확인합니다.', 'DURATION': '10분', 'IMAGE_SRC': image_a, 'RESULT_TEXT': '핵심 행동이 선명한 첫 화면'},
        {'page_type': 'slide', 'layout': 'fullbleed', 'TITLE': '작은 아이디어가 실제 변화가 됩니다', 'SUBTITLE': '오늘 만든 화면을 친구와 함께 검증해 봅시다.', 'IMAGE_SRC': image_b, 'BADGE': '도전'},
        {'page_type': 'slide', 'layout': 'matrix', 'TITLE': '아이디어 우선순위 정하기', 'SUBTITLE': '효과와 구현 난이도를 함께 봅니다.', 'MATRIX_ITEMS': [
            {'icon': 'A', 'label': '먼저', 'title': '효과 큼·쉬움', 'desc': '첫 버전에 바로 넣습니다.'},
            {'icon': 'B', 'label': '계획', 'title': '효과 큼·어려움', 'desc': '작은 단계로 나눕니다.'},
            {'icon': 'C', 'label': '선택', 'title': '효과 작음·쉬움', 'desc': '시간이 남으면 넣습니다.'},
            {'icon': 'D', 'label': '제외', 'title': '효과 작음·어려움', 'desc': '이번에는 만들지 않습니다.'},
        ]},
        {'page_type': 'slide', 'layout': 'vs_ox', 'TITLE': 'AI 결과를 다루는 태도', 'O_TITLE': '좋은 태도', 'O_ITEMS': [
            {'text': '결과를 직접 확인합니다.'}, {'text': '틀린 부분을 구체적으로 말합니다.'},
        ], 'X_TITLE': '피할 태도', 'X_ITEMS': [
            {'text': '첫 결과를 그대로 믿습니다.'}, {'text': '막연히 다시 해 달라고 합니다.'},
        ], 'BOTTOM_TAKEAWAY': 'AI의 답보다 검증하는 사람의 판단이 중요합니다.'},
        {'page_type': 'slide', 'layout': 'roadmap', 'TITLE': '문제를 해결하는 네 단계', 'ROADMAP_ITEMS': [
            {'label': '문제 찾기', 'desc': '사용자의 불편을 관찰합니다.'},
            {'label': '흐름 설계', 'desc': '필요한 행동의 순서를 정합니다.'},
            {'label': '빠른 구현', 'desc': '핵심 기능부터 작동시킵니다.'},
            {'label': '결과 검증', 'desc': '사용자 관점에서 다시 확인합니다.'},
        ]},
        {'page_type': 'slide', 'layout': 'activity_instruction', 'TITLE': '활동 준비', 'INSTRUCTION': '학습지 1번을 읽고 짝과 답을 비교하세요.', 'WORKSHEET_REF': '학생용 활동지 1쪽', 'TIMER_MINUTES': 3, 'THINK_QUESTION': '답을 고른 근거를 한 문장으로 설명할 수 있나요?'},
        {'page_type': 'slide', 'layout': 'share_prompt', 'TITLE': '생각을 나눠 봅시다', 'INSTRUCTION': '짝의 설명에서 새롭게 알게 된 점을 찾으세요.', 'QUESTIONS': ['어떤 근거가 가장 설득력 있었나요?', '내 생각과 달랐던 점은 무엇인가요?']},
        {'page_type': 'slide', 'layout': 'video_hook', 'TITLE': '영상에서 특징 찾기', 'EMBED_URL': 'about:blank', 'PURPOSE': '영상 속 장면에서 문제 상황을 찾아봅시다.', 'STUDENT_TASK': '눈에 띄는 특징을 한 문장으로 적습니다.'},
        {'page_type': 'slide', 'layout': 'video_link_card', 'TITLE': '관련 영상 더 보기', 'WATCH_URL': 'https://www.youtube.com/', 'THUMBNAIL_URL': image_b, 'PURPOSE': '다른 사례와 비교해 봅시다.', 'STUDENT_TASK': '공통점과 차이점을 하나씩 찾습니다.'},
    ]
    pages.extend({'page_type': 'slide', 'layout': 'activity', 'ACTIVITY_REF': item['id']} for item in activities)
    pages.extend([
        {'page_type': 'worksheet', 'ACTIVITY_REFS': ['ox', 'cloze', 'matching', 'table', 'short']},
        {'page_type': 'worksheet', 'BLOCKS': [{'block_type': 'reflection_checklist', 'title': '스스로 점검하기', 'items': [
            {'text': '문제와 해결 방법을 설명할 수 있나요?'}, {'text': '친구의 의견을 듣고 화면을 고쳤나요?'},
        ]}]},
        {'page_type': 'answer_key', 'ACTIVITY_REFS': ['ox', 'cloze', 'matching', 'table', 'short']},
    ])

    covered = {page['layout'] for page in pages if page.get('page_type') == 'slide' and page.get('layout') != 'activity'}
    covered.update(ACTIVITY_LAYOUT_BY_BLOCK.values())
    missing = set(REQUIRED_LAYOUT_FIELDS) - covered - {'activity_prompt'}
    if missing:
        raise AssertionError(f'대표 회귀 페이지 누락: {sorted(missing)}')
    return {'meta': {'title': 'Slide layout regression'}, 'activities': activities, 'pages': pages}


def variants():
    for theme in FIXED_THEMES:
        yield theme, {'theme': theme}
    for font in FONT_PRESETS:
        yield f'font_{font}', {
            'theme_colors': {
                'bg': '#F8FAFC', 'bg_secondary': '#FFFFFF', 'text': '#172033',
                'text_secondary': '#475569', 'accent': '#2563EB', 'accent_secondary': '#F59E0B',
                'font_preset': font, 'card_style_preset': 'business_clean',
                'image_frame_preset': 'business', 'icon_preset': 'business',
                'highlight_style': 'friendly', 'takeaway_style': 'friendly', 'motion_preset': 'friendly',
            }
        }


async def run(output_dir, selected):
    output_dir.mkdir(parents=True, exist_ok=True)
    base_plan = representative_plan()
    failures = []
    summaries = {}

    for name, meta in variants():
        if selected and name not in selected:
            continue
        variant_dir = output_dir / name
        variant_dir.mkdir(parents=True, exist_ok=True)
        plan = deepcopy(base_plan)
        plan['meta'].update(meta)
        plan_path = variant_dir / 'slide_plan.json'
        html_path = variant_dir / 'index.html'
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
        build_html(str(plan_path), str(html_path))

        try:
            await capture_pngs(str(html_path), str(variant_dir / 'captures'))
        except RuntimeError as error:
            failures.append({'variant': name, 'error': str(error)})

        report_path = variant_dir / 'captures' / 'qa-report.json'
        if report_path.exists():
            summaries[name] = json.loads(report_path.read_text(encoding='utf-8'))['summary']

    summary = {'variants': summaries, 'failures': failures}
    (output_dir / 'matrix-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    if failures:
        raise RuntimeError(f'레이아웃 회귀 실패 {len(failures)}개: {[item["variant"] for item in failures]}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('--variant', action='append', default=[], help='특정 변형만 실행')
    args = parser.parse_args()
    asyncio.run(run(args.output_dir.resolve(), set(args.variant)))


if __name__ == '__main__':
    main()
