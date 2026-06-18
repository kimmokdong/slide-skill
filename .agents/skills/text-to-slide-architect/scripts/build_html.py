#!/usr/bin/env python3
"""JSON 설계도(slide_plan.json)를 읽어 Reveal.js HTML 슬라이드로 렌더링하는 스크립트.

v2.0 — 동적 테마(theme_colors), BOTTOM_TAKEAWAY, 아이콘 불릿, 섹션 헤더 지원

사용법:
    python build_html.py <입력_json> <출력_html>
"""

import sys
import os
import json
import re


def load_template(name: str) -> str:
    """템플릿 파일을 읽어옵니다."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, '..', 'templates', f'{name}.html')
    if not os.path.exists(template_path):
        # layout_ 접두어 시도
        template_path = os.path.join(script_dir, '..', 'templates', f'layout_{name}.html')

    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_theme(theme_name: str) -> str:
    """테마 CSS를 읽어옵니다."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    theme_path = os.path.join(script_dir, '..', 'templates', 'themes', f'theme_{theme_name}.css')

    if os.path.exists(theme_path):
        with open(theme_path, 'r', encoding='utf-8') as f:
            css = f.read()
            return f"<style>\n{css}\n</style>"
    return ""


def is_light_color(hex_color: str) -> bool:
    """색상이 밝은 계열인지 판정합니다 (YIQ 방식)."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    if len(hex_color) != 6:
        return True
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000
        return yiq >= 128
    except ValueError:
        return True


def generate_dynamic_theme_css(theme_colors: dict) -> str:
    """meta.theme_colors에서 동적 CSS 변수를 생성합니다.
    
    theme_colors 스키마:
    {
        "bg": "#F0F4FF",           // 60% 배경색
        "text": "#1E293B",         // 30% 텍스트 및 구조색
        "accent": "#3B82F6",       // 10% 포인트 강조색
        "bg_secondary": "#E2E8F0", // (선택) 보조 배경
        "accent_secondary": "#7C3AED", // (선택) 보조 강조
        "decorations": ["circles", "waves", "dots"]  // (선택) CSS 장식 요소
    }
    """
    if not theme_colors:
        return ""

    bg = theme_colors.get('bg', '#0F172A')
    bg_secondary = theme_colors.get('bg_secondary', bg)
    text = theme_colors.get('text', '#F1F5F9')
    text_secondary = theme_colors.get('text_secondary', text)
    accent = theme_colors.get('accent', '#3B82F6')
    accent_secondary = theme_colors.get('accent_secondary', accent)

    # 밝은 배경 대비 가드 적용
    is_light = is_light_color(bg)
    card_bg = "rgba(255, 255, 255, 0.65)" if is_light else "rgba(255, 255, 255, 0.08)"
    card_border = "rgba(0, 0, 0, 0.12)" if is_light else "rgba(255, 255, 255, 0.15)"

    # 이미지 프레임 스타일 동적 파생
    frame_bg = "#ffffff" if is_light else "rgba(255, 255, 255, 0.05)"
    frame_border = f"1px solid {card_border}"
    frame_shadow = "0 8px 24px rgba(0, 0, 0, 0.08)" if is_light else "0 10px 30px rgba(0, 0, 0, 0.3)"
    frame_radius = "16px"
    frame_dots = "flex"

    # 60-30-10 기반 자동 파생 색상
    css = f"""<style>
/* ===== 동적 테마 (60-30-10 Rule) ===== */
:root {{
    --color-bg: {bg};
    --color-bg-secondary: {bg_secondary};
    --color-text: {text};
    --color-text-secondary: {text_secondary};
    --color-accent: {accent};
    --color-accent-secondary: {accent_secondary};
    --color-gradient: linear-gradient(135deg, {accent} 0%, {accent_secondary} 100%);
    --color-card-bg: {card_bg};
    --color-card-border: {card_border};
    --color-muted: {text_secondary};
    
    /* 이미지 프레임 (테마 제어 요소) */
    --image-frame-bg: {frame_bg};
    --image-frame-border: {frame_border};
    --image-frame-shadow: {frame_shadow};
    --image-frame-radius: {frame_radius};
    --image-frame-dots-display: {frame_dots};
}}

.reveal {{
    background: var(--color-bg);
    color: var(--color-text);
}}

.reveal h1, .reveal h2, .reveal h3 {{
    color: var(--color-text);
}}

.reveal h1 {{
    background: var(--color-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.reveal p, .reveal li {{
    color: var(--color-text-secondary);
}}

.card {{
    background: var(--color-card-bg);
    border-color: var(--color-card-border);
}}

.bullet-list li::before {{
    background: var(--color-accent);
}}

.stat-number {{
    background: var(--color-gradient);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.summary-list li::before {{
    background: var(--color-gradient);
}}

.vs-badge {{
    background: var(--color-gradient) !important;
}}
"""

    # CSS 장식 요소 (주제별 배경 패턴)
    decorations = theme_colors.get('decorations', [])
    if isinstance(decorations, list):
        decorations = decorations.copy()
    else:
        decorations = []
        
    bg_pattern = theme_colors.get('bg_pattern_style')
    if bg_pattern:
        if bg_pattern == 'grid' and 'grid_lines' not in decorations:
            decorations.append('grid_lines')
        elif bg_pattern not in decorations:
            decorations.append(bg_pattern)

    if decorations:
        css += "\n/* --- 주제별 CSS 장식 요소 --- */\n"
        for deco in decorations:
            if deco == 'circles':
                css += """.reveal-viewport::before {
    content: '';
    position: absolute;
    top: -80px;
    right: -80px;
    width: 250px;
    height: 250px;
    border-radius: 50%;
    background: var(--color-accent);
    opacity: 0.12;
    pointer-events: none;
    z-index: 0;
}
.reveal-viewport::after {
    content: '';
    position: absolute;
    bottom: -60px;
    left: -60px;
    width: 180px;
    height: 180px;
    border-radius: 50%;
    background: var(--color-accent-secondary);
    opacity: 0.10;
    pointer-events: none;
    z-index: 0;
}
"""
            elif deco == 'waves':
                css += """.reveal::before {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 100%;
    height: 120px;
    background: linear-gradient(135deg, transparent 33.33%, var(--color-accent) 33.33%, var(--color-accent) 66.66%, transparent 66.66%);
    opacity: 0.12;
    pointer-events: none;
    z-index: 0;
}
"""
            elif deco == 'dots':
                css += """.reveal::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: radial-gradient(var(--color-accent) 2px, transparent 2px);
    background-size: 30px 30px;
    opacity: 0.12;
    pointer-events: none;
    z-index: 0;
}
"""
            elif deco == 'grid_lines':
                css += """.reveal::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: 
        linear-gradient(var(--color-accent) 1px, transparent 1px),
        linear-gradient(90deg, var(--color-accent) 1px, transparent 1px);
    background-size: 60px 60px;
    opacity: 0.15;
    pointer-events: none;
    z-index: 0;
}
"""
            elif deco == 'corner_accent':
                css += """.reveal .slides section::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 120px;
    height: 6px;
    background: var(--color-gradient);
    border-radius: 0 0 6px 0;
    pointer-events: none;
    z-index: 1;
}
.reveal .slides section::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 6px;
    height: 80px;
    background: var(--color-gradient);
    border-radius: 0 0 6px 0;
    pointer-events: none;
    z-index: 1;
}
"""

    css += "</style>"
    return css


def extract_percentage(value_str: str) -> int:
    """수치 텍스트로부터 게이지 바에 채울 백분율 값을 추출합니다."""
    # 1. % 기호가 있으면 숫자 추출
    if '%' in value_str:
        match = re.search(r'([\d\.]+)', value_str)
        if match:
            try:
                return int(float(match.group(1)))
            except ValueError:
                pass
    # 2. '점'이 들어있고 숫자가 있으면
    if '점' in value_str:
        match = re.search(r'([\d\.]+)', value_str)
        if match:
            try:
                val = float(match.group(1))
                if val <= 5.0:
                    return int((val / 5.0) * 100)
                elif val <= 10.0:
                    return int((val / 10.0) * 100)
                elif val <= 100.0:
                    return int(val)
            except ValueError:
                pass
    # 3. 그 외 일반 숫자인 경우
    match = re.search(r'([\d\.]+)', value_str)
    if match:
        try:
            val = float(match.group(1))
            if val == 0:
                return 0
            if val > 0 and val <= 5.0:
                return int((val / 5.0) * 100)
            elif val > 5.0 and val <= 10.0:
                return int((val / 10.0) * 100)
            elif val > 10.0 and val <= 100.0:
                return int(val)
            else:
                return 100
        except ValueError:
            pass
    return 0


def process_list(items, tag='li', class_name=''):
    """리스트 데이터를 HTML 태그로 변환합니다."""
    if not items:
        return ""

    cls_attr = f' class="{class_name}"' if class_name else ''
    result = []

    for item in items:
        if isinstance(item, str):
            result.append(f"<{tag}{cls_attr}>{item}</{tag}>")
        elif isinstance(item, dict):
            # 아이콘 불릿 지원: {"icon": "💡", "text": "내용"}
            if 'icon' in item and 'text' in item:
                icon = item['icon']
                text = item['text']
                result.append(f'<li class="icon-bullet"><span class="bullet-icon">{icon}</span><span class="bullet-text">{text}</span></li>')
            # 복합 객체 처리
            elif tag == 'timeline-item':
                result.append(f'''<div class="timeline-item">
                    <div class="timeline-title">{item.get('title', '')}</div>
                    <div class="timeline-desc">{item.get('desc', '')}</div>
                </div>''')
            elif tag == 'stat-item':
                value_str = item.get('value', '')
                label_str = item.get('label', '')
                percentage = extract_percentage(value_str)
                # 수치가 0%인 텍스트인 경우, 클릭 시 100% 차오르게 기본 타겟을 100으로 설정
                target_percent = percentage if percentage > 0 else 100
                result.append(f'''<div class="card stat-card-button" onclick="clickStatCard(this, {target_percent})" style="text-align: center; display: flex; flex-direction: column; justify-content: space-between; padding: 1.2em 1em; cursor: pointer; transition: all 0.2s ease; flex: 1; max-width: 350px; min-width: 220px;">
                    <div class="stat-number" style="color: var(--color-accent); font-size: 1.8em; font-weight: 900; line-height: 1.1; margin-bottom: 0.1em;">{value_str}</div>
                    <div class="stat-label" style="font-size: 0.8em; color: var(--color-text-secondary); font-weight: 500; margin-bottom: 0.6em; word-break: keep-all;">{label_str}</div>
                    <div class="stat-gauge-container" style="background: rgba(0,0,0,0.05); border-radius: 4px; height: 8px; overflow: hidden; width: 100%; margin-top: auto;">
                        <div class="stat-gauge-bar" data-target-width="{percentage}%" style="background: var(--color-gradient); height: 100%; width: 0%; border-radius: 4px; transition: width 1.2s cubic-bezier(0.1, 0.8, 0.3, 1);"></div>
                    </div>
                </div>''')
            elif tag == 'quiz-option':
                result.append(f'<div class="quiz-option card">{item.get("text", "")}</div>')
            # matrix 아이템: {"label": "텍스트", "quadrant": 1~4}
            elif tag == 'matrix-item':
                label = item.get('label', '')
                icon = item.get('icon', '')
                desc = item.get('desc', '')
                icon_html = f'<div class="matrix-icon">{icon}</div>' if icon else ''
                desc_html = f'<div class="matrix-desc">{desc}</div>' if desc else ''
                result.append(f'<div class="matrix-cell card">{icon_html}<div class="matrix-label">{label}</div>{desc_html}</div>')
            # vs_ox 아이템
            elif tag == 'ox-item':
                text = item.get('text', '')
                marker = item.get('marker', 'O')
                marker_class = 'marker-o' if marker.upper() == 'O' else 'marker-x'
                result.append(f'<div class="ox-item"><span class="ox-marker {marker_class}">{marker.upper()}</span><span class="ox-text">{text}</span></div>')

    return "\n".join(result)


def render_bottom_takeaway(slide_data: dict) -> str:
    """BOTTOM_TAKEAWAY가 있으면 하단 요약 바 HTML을 생성합니다."""
    takeaway = slide_data.get('BOTTOM_TAKEAWAY', '')
    if not takeaway:
        return ''
    return f'''<div class="bottom-takeaway-bar">
    <div class="takeaway-content">{takeaway}</div>
</div>'''


def render_section_header(slide_data: dict) -> str:
    """SECTION_HEADER가 있으면 상단에 현재 섹션명을 표시합니다."""
    header = slide_data.get('SECTION_HEADER', '')
    if not header:
        return ''
    return f'<div class="section-header-tag">{header}</div>'


def render_slide(slide_data: dict) -> str:
    """단일 슬라이드 데이터를 HTML로 렌더링합니다."""
    slide_type = slide_data.get('layout', slide_data.get('type', 'title'))

    try:
        template = load_template(slide_type)
    except FileNotFoundError:
        print(f"경고: {slide_type} 레이아웃 템플릿을 찾을 수 없습니다. 기본 title로 대체합니다.")
        template = load_template('title')

    # 특수 처리 (리스트 등)
    data = slide_data.copy()
    if slide_type == 'tutorial':
        raw_title = str(data.get('TITLE', ''))
        data['DISPLAY_TITLE'] = re.sub(r'^\s*\d+\s*단계\s*[:：;；]\s*', '', raw_title)
    elif 'TITLE' in data:
        data['DISPLAY_TITLE'] = data.get('TITLE', '')

    if 'BULLET_ITEMS' in data:
        data['BULLET_ITEMS'] = process_list(data['BULLET_ITEMS'], 'li')

    if 'LEFT_ITEMS' in data:
        data['LEFT_ITEMS'] = process_list(data['LEFT_ITEMS'], 'li')

    if 'RIGHT_ITEMS' in data:
        data['RIGHT_ITEMS'] = process_list(data['RIGHT_ITEMS'], 'li')

    if 'SUMMARY_ITEMS' in data:
        data['SUMMARY_ITEMS'] = process_list(data['SUMMARY_ITEMS'], 'li')

    if 'TIMELINE_ITEMS' in data:
        data['TIMELINE_ITEMS'] = process_list(data['TIMELINE_ITEMS'], 'timeline-item')

    if 'STAT_ITEMS' in data:
        data['STAT_ITEMS'] = process_list(data['STAT_ITEMS'], 'stat-item')

    if 'QUIZ_OPTIONS' in data:
        answer_index = data.get('ANSWER_INDEX', 0)
        quiz_options = data['QUIZ_OPTIONS']
        options_html_parts = []
        for i, option in enumerate(quiz_options):
            option_text = option.get('text', option) if isinstance(option, dict) else option
            is_correct = "true" if i == answer_index else "false"
            options_html_parts.append(f'''<div class="quiz-option card button-type" onclick="checkQuizAnswer(this, {is_correct})" style="cursor: pointer; transition: all 0.2s ease; margin-bottom: 0.3em; padding: 0.6em 1em; text-align: center; display: flex; align-items: center; justify-content: center; gap: 0.8em; border-radius: 12px; background: var(--color-card-bg); border: 1px solid var(--color-card-border); box-shadow: 0 4px 12px rgba(0,0,0,0.03); font-size: 0.8em;">
                <span class="option-marker" style="display: inline-flex; align-items: center; justify-content: center; width: 1.8em; height: 1.8em; border-radius: 50%; background: rgba(0,0,0,0.05); font-weight: 700; font-size: 0.85em; flex-shrink: 0; transition: background 0.2s ease, color 0.2s ease;">{chr(65+i)}</span>
                <span class="option-text" style="word-break: keep-all; font-weight: 500; line-height: 1.3; text-align: center;">{option_text}</span>
            </div>''')
        data['QUIZ_OPTIONS'] = '\n'.join(options_html_parts)

    # 신규: 매트릭스 아이템
    if 'MATRIX_ITEMS' in data:
        data['MATRIX_ITEMS'] = process_list(data['MATRIX_ITEMS'], 'matrix-item')

    # 신규: O/X 아이템
    if 'O_ITEMS' in data or 'X_ITEMS' in data:
        ox_items_raw = []
        ox_items_raw.extend(data.get('O_ITEMS', []) or [])
        ox_items_raw.extend(data.get('X_ITEMS', []) or [])
        ox_texts = []
        for ox_item in ox_items_raw:
            if isinstance(ox_item, dict):
                ox_texts.append(str(ox_item.get('text', '')))
            else:
                ox_texts.append(str(ox_item))
        max_count = max(len(data.get('O_ITEMS', []) or []), len(data.get('X_ITEMS', []) or []), 1)
        max_len = max([len(text) for text in ox_texts] or [0])
        if max_count <= 2 and max_len <= 20:
            data['OX_DENSITY_CLASS'] = 'ox-roomy'
        elif max_count <= 3 and max_len <= 28:
            data['OX_DENSITY_CLASS'] = 'ox-balanced'
        else:
            data['OX_DENSITY_CLASS'] = 'ox-dense'

    if 'O_ITEMS' in data:
        data['O_ITEMS'] = process_list(data['O_ITEMS'], 'ox-item')
    if 'X_ITEMS' in data:
        data['X_ITEMS'] = process_list(data['X_ITEMS'], 'ox-item')

    # 신규: 로드맵 아이템
    if 'ROADMAP_ITEMS' in data:
        roadmap_items = data['ROADMAP_ITEMS']
        roadmap_html_parts = []
        for i, item in enumerate(roadmap_items):
            if isinstance(item, dict):
                label = item.get('label', f'Step {i+1}')
                desc = item.get('desc', '')
                desc_html = f'<div class="roadmap-desc">{desc}</div>' if desc else ''
                roadmap_html_parts.append(f'''<div class="roadmap-step">
                    <div class="roadmap-num">{i+1}</div>
                    <div class="roadmap-label">{label}</div>
                    {desc_html}
                </div>''')
            else:
                roadmap_html_parts.append(f'''<div class="roadmap-step">
                    <div class="roadmap-num">{i+1}</div>
                    <div class="roadmap-label">{item}</div>
                </div>''')
            if i < len(roadmap_items) - 1:
                roadmap_html_parts.append('<div class="roadmap-connector"></div>')
        data['ROADMAP_ITEMS'] = '\n'.join(roadmap_html_parts)

    # 스텝퍼 (교육/연수 전용)
    if 'STEPPER_ITEMS' in data:
        stepper_items = data['STEPPER_ITEMS']
        stepper_html_parts = []
        for i, step_info in enumerate(stepper_items):
            if isinstance(step_info, dict):
                label = step_info.get('label', f'Step {i+1}')
                state = step_info.get('state', 'inactive')  # active, completed, inactive
            else:
                label = str(step_info)
                state = 'inactive'

            css_class = f'stepper-step {state}'
            step_html = f'<div class="{css_class}"><span class="step-num">{i+1}</span><span>{label}</span></div>'
            stepper_html_parts.append(step_html)
            # 마지막 아이템이 아니면 커넥터 추가
            if i < len(stepper_items) - 1:
                stepper_html_parts.append('<div class="stepper-connector"></div>')
        data['STEPPER_ITEMS'] = '\n'.join(stepper_html_parts)

    # 공통 요소 렌더링
    bottom_takeaway_html = render_bottom_takeaway(data)
    section_header_html = render_section_header(data)
    data['BOTTOM_TAKEAWAY_HTML'] = bottom_takeaway_html
    data['SECTION_HEADER_HTML'] = section_header_html

    # 템플릿 변수 치환
    html = template

    # 조건부 블록 ({{#if VAR}} ... {{/if}}) 처리 (Cross-boundary 버그 수정)
    for key in list(data.keys()):
        val = data[key]
        pattern_block = r'\{\{\#if ' + key + r'\}\}(.*?)\{\{\/if\}\}'
        
        def replace_block(match):
            content = match.group(1)
            # content 안에 {{else}} 가 있는지 확인
            parts = re.split(r'\{\{\s*else\s*\}\}', content, maxsplit=1)
            if val:
                return parts[0] # 참일 때는 else 앞부분 반환
            else:
                return parts[1] if len(parts) > 1 else '' # 거짓일 때는 else 뒷부분 반환 (없으면 빈 문자열)
                
        html = re.sub(pattern_block, replace_block, html, flags=re.DOTALL)

    # 남은 if 블록 제거 (데이터에 없는 키)
    html = re.sub(r'\{\{\#if [A-Z_]+\}\}(.*?)\{\{\/if\}\}', lambda m: re.split(r'\{\{\s*else\s*\}\}', m.group(1), maxsplit=1)[1] if len(re.split(r'\{\{\s*else\s*\}\}', m.group(1), maxsplit=1)) > 1 else '', html, flags=re.DOTALL)

    # 단순 치환
    for key, value in data.items():
        html = html.replace(f'{{{{{key}}}}}', str(value))

    # 채워지지 않은 변수 지우기
    html = re.sub(r'{{[A-Z_]+}}', '', html)

    # BOTTOM_TAKEAWAY가 템플릿에 {{BOTTOM_TAKEAWAY_HTML}} 자리가 없으면 slide-container 닫는 태그 직전에 주입
    if bottom_takeaway_html and '{{BOTTOM_TAKEAWAY_HTML}}' not in template and bottom_takeaway_html not in html:
        # 마지막 </div></section> 또는 </div>\n<aside> 사이에 넣기 위해 정규식 사용
        html = re.sub(r'(</div>\s*(?:<aside[^>]*>.*?</aside>\s*)?</section>)', rf'{bottom_takeaway_html}\n\1', html, count=1, flags=re.DOTALL)
        if bottom_takeaway_html not in html:
            # 실패 시 기존대로 fallback (잘못된 위치일지라도 렌더링은 되게)
            html = html.replace('</section>', f'{bottom_takeaway_html}\n</section>')

    # SECTION_HEADER가 템플릿에 자리가 없으면 <section> 바로 뒤에 주입
    if section_header_html and '{{SECTION_HEADER_HTML}}' not in template and section_header_html not in html:
        html = re.sub(r'(<section[^>]*>)', rf'\1\n{section_header_html}', html, count=1)

    return html


def build_html(input_json: str, output_html: str) -> None:
    """slide_plan.json을 읽어 HTML을 생성합니다."""

    if not os.path.exists(input_json):
        print(f"오류: {input_json} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    with open(input_json, 'r', encoding='utf-8') as f:
        plan = json.load(f)

    meta = plan.get('meta', {})
    theme = meta.get('theme', 'tech_blue')
    theme_colors = meta.get('theme_colors', None)
    presentation_title = meta.get('title', '프레젠테이션')

    slides_data = plan.get('slides', [])

    # 슬라이드 렌더링
    rendered_slides = []
    current_section_header = ""
    for slide in slides_data:
        if 'SECTION_HEADER' in slide:
            current_section_header = slide['SECTION_HEADER']
        elif current_section_header:
            slide['SECTION_HEADER'] = current_section_header

        rendered_slides.append(render_slide(slide))

    slides_content = "\n".join(rendered_slides)

    # 베이스 템플릿 로드 및 최종 조립
    base_html = load_template('base')

    # 테마 결정: theme_colors가 있으면 동적 테마 우선, 없으면 기존 고정 테마
    if theme_colors:
        theme_css = generate_dynamic_theme_css(theme_colors)
        print(f"   테마 모드: 동적 (60-30-10 커스텀)")
    else:
        theme_css = load_theme(theme)
        print(f"   테마 모드: 고정 ({theme})")

    final_html = base_html.replace('{{PRESENTATION_TITLE}}', presentation_title)
    final_html = final_html.replace('{{THEME_CSS}}', theme_css)
    final_html = final_html.replace('{{SLIDES_CONTENT}}', slides_content)

    # 출력 폴더 생성
    output_dir = os.path.dirname(output_html)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(final_html)

    print(f"[SUCCESS] HTML 빌드 완료: {output_html}")
    print(f"   슬라이드 수: {len(slides_data)}장")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("사용법: python build_html.py <입력_json> <출력_html>")
        sys.exit(1)

    build_html(sys.argv[1], sys.argv[2])
