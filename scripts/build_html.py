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
from html import escape


INCLUDE_PATTERN = re.compile(r'\{\{\s*INCLUDE:([^}]+)\s*\}\}')


def get_template_root() -> str:
    """템플릿 루트 디렉터리 경로를 반환합니다."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.realpath(os.path.join(script_dir, '..', 'templates'))


def expand_template_includes(text: str, root_dir: str = None, stack: tuple = (), depth: int = 0, max_depth: int = 20) -> str:
    """{{INCLUDE:path}} 지시자를 템플릿 루트 기준으로 재귀 확장합니다."""
    root_dir = os.path.realpath(root_dir or get_template_root())

    if depth > max_depth:
        chain = " -> ".join(stack)
        raise RecursionError(f"include 최대 깊이({max_depth})를 초과했습니다: {chain}")

    def replace_include(match):
        include_name = match.group(1).strip()
        normalized = include_name.replace('\\', os.sep).replace('/', os.sep)

        if os.path.isabs(normalized):
            raise ValueError(f"include 경로는 상대 경로만 허용됩니다: {include_name}")

        include_path = os.path.realpath(os.path.join(root_dir, normalized))
        if os.path.commonpath([root_dir, include_path]) != root_dir:
            raise ValueError(f"include 경로가 templates 폴더 밖을 가리킵니다: {include_name}")

        if include_path in stack:
            chain = " -> ".join(list(stack) + [include_path])
            raise RecursionError(f"순환 include가 감지되었습니다: {chain}")

        if not os.path.isfile(include_path):
            raise FileNotFoundError(f"include 파일을 찾을 수 없습니다: {include_name}")

        with open(include_path, 'r', encoding='utf-8') as f:
            include_text = f.read()

        expanded_text = expand_template_includes(
            include_text,
            root_dir=root_dir,
            stack=stack + (include_path,),
            depth=depth + 1,
            max_depth=max_depth
        )

        ext = os.path.splitext(include_name)[1].lower()
        if ext in ['.css', '.js']:
            start_comment = f"/* --- START INCLUDE: {include_name} --- */\n"
            end_comment = f"\n/* --- END INCLUDE: {include_name} --- */"
        elif ext in ['.html']:
            start_comment = f"<!-- --- START INCLUDE: {include_name} --- -->\n"
            end_comment = f"\n<!-- --- END INCLUDE: {include_name} --- -->"
        else:
            start_comment = ""
            end_comment = ""

        return f"{start_comment}{expanded_text}{end_comment}"

    return INCLUDE_PATTERN.sub(replace_include, text)


def load_template(name: str) -> str:
    """템플릿 파일을 읽어옵니다."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, '..', 'templates', f'{name}.html')
    if not os.path.exists(template_path):
        # layout_ 접두어 시도
        template_path = os.path.join(script_dir, '..', 'templates', f'layout_{name}.html')

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    return expand_template_includes(
        template,
        root_dir=get_template_root(),
        stack=(os.path.realpath(template_path),)
    )


def assert_no_unresolved_includes(html: str) -> None:
    """최종 HTML 안에 처리되지 않은 include 지시자가 남아 있으면 중단합니다."""
    match = INCLUDE_PATTERN.search(html)
    if match:
        raise ValueError(f"처리되지 않은 include 지시자가 남았습니다: {match.group(0)}")


def load_theme(theme_name: str) -> str:
    """테마 CSS를 읽어옵니다."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    theme_path = os.path.join(script_dir, '..', 'templates', 'themes', f'theme_{theme_name}.css')

    if os.path.exists(theme_path):
        with open(theme_path, 'r', encoding='utf-8') as f:
            css = f.read()
            return f'<style id="meta-theme-style">\n{css}\n</style>'
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
    """meta.theme_colors에서 동적 CSS 변수 및 프리셋 룰을 생성합니다."""
    if not theme_colors:
        return ""

    bg = theme_colors.get('bg', '#F8FAFF')
    bg_secondary = theme_colors.get('bg_secondary', bg)
    text = theme_colors.get('text', '#1E293B')
    text_secondary = theme_colors.get('text_secondary', text)
    accent = theme_colors.get('accent', '#4F46E5')
    accent_secondary = theme_colors.get('accent_secondary', accent)

    # 밝은 배경 대비 가드 적용
    is_light = is_light_color(bg)
    card_bg = "rgba(255, 255, 255, 0.65)" if is_light else "rgba(255, 255, 255, 0.08)"
    card_border = "rgba(0, 0, 0, 0.12)" if is_light else "rgba(255, 255, 255, 0.15)"

    # CSS 하드코딩을 중단하고 프리셋 이름만 추출하여 HTML 클래스 주입으로 대체 (SSOT 원칙 적용)
    frame_preset = theme_colors.get('image_frame_preset', 'business')
    card_preset = theme_colors.get('card_style_preset', 'business_clean')
    icon_preset = theme_colors.get('icon_preset', 'business')
    highlight_preset = theme_colors.get('highlight_style', theme_colors.get('strong_style', 'friendly'))
    takeaway_preset = theme_colors.get('takeaway_style', 'friendly')
    motion_preset = theme_colors.get('motion_preset', 'friendly')

    # 폰트 프리셋 매칭 (유일하게 :root에 직접 반영되어야 하는 값)
    font_preset = theme_colors.get('font_preset', 'friendly')
    font_stack = "'Outfit', 'Noto Sans KR', sans-serif"
    if font_preset == 'cyber':
        font_stack = "'Orbitron', 'Nanum Square Neo', sans-serif"
    elif font_preset == 'classic':
        font_stack = "'Playfair Display', 'Nanum Myeongjo', serif"
    elif font_preset == 'editorial':
        font_stack = "'Montserrat', 'Pretendard', sans-serif"
    elif font_preset == 'chalkboard':
        font_stack = "'Caveat', 'Nanum Pen Script', cursive"

    # 60-30-10 기반 자동 파생 색상 및 프리셋 CSS 통합 조립
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
    --font-primary: {font_stack};
}}


.reveal {{
    background: var(--color-bg);
    color: var(--color-text);
    font-family: var(--font-primary) !important;
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

/* h1 내부 strong의 투명화 상속 차단 — hero/closing 표지에서 형광펜 글자가 사라지는 버그 근본 해결 */
.reveal h1 strong {{
    -webkit-text-fill-color: var(--color-text);
    background-clip: initial;
    -webkit-background-clip: initial;
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
</style>"""
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


def editable_attrs(edit_id: str) -> str:
    """Return stable attributes used by browser-side direct editing."""
    if not edit_id:
        return ""
    return f' data-edit-id="{escape(str(edit_id), quote=True)}"'


def merge_inline_style(existing_style: str, new_rules: dict) -> str:
    rules = {}
    for part in (existing_style or "").split(';'):
        if ':' in part:
            key, value = part.split(':', 1)
            rules[key.strip()] = value.strip()
    rules.update({key: value for key, value in new_rules.items() if value})
    return '; '.join(f'{key}: {value}' for key, value in rules.items())


def get_first_value(data: dict, keys: list, default=''):
    for key in keys:
        value = data.get(key)
        if value is not None and value != '':
            return value
    return default


def apply_style_overrides(rendered_html: str, style_overrides: dict) -> str:
    if not isinstance(style_overrides, dict) or not style_overrides:
        return rendered_html

    for edit_id, style in style_overrides.items():
        if not isinstance(style, dict):
            continue
        font_size = style.get('fontSize')
        if not font_size:
            continue
        font_size_value = str(font_size).strip()
        if '!important' not in font_size_value:
            font_size_value = f'{font_size_value} !important'
        pattern = re.compile(r'(<[^>]+data-edit-id="' + re.escape(str(edit_id)) + r'"[^>]*)(>)')

        def replace_tag(match):
            tag_open = match.group(1)
            tag_close = match.group(2)
            style_match = re.search(r'style="([^"]*)"', tag_open)
            merged_style = merge_inline_style(style_match.group(1) if style_match else "", {'font-size': font_size_value})
            if style_match:
                tag_open = tag_open[:style_match.start()] + f'style="{merged_style}"' + tag_open[style_match.end():]
            else:
                tag_open = f'{tag_open} style="{merged_style}"'
            if 'data-style-locked=' not in tag_open:
                tag_open = f'{tag_open} data-style-locked="true"'
            return tag_open + tag_close

        rendered_html = pattern.sub(replace_tag, rendered_html)
    return rendered_html


def process_list(items, tag='li', class_name='', edit_key='', default_marker='O', default_marker_class='marker-o', sequential=False):
    """리스트 데이터를 HTML 태그로 변환합니다."""
    if not items:
        return ""

    if sequential:
        class_name = f"{class_name} fragment" if class_name else "fragment"

    cls_attr = f' class="{class_name}"' if class_name else ''
    result = []

    for index, item in enumerate(items):
        item_edit_id = f"{edit_key}[{index}]" if edit_key else ""
        if tag == 'ox-item':
            if isinstance(item, dict):
                text = item.get('text', '')
                marker = item.get('marker', default_marker)
                marker_class = item.get('marker_class') or default_marker_class
            else:
                text = str(item)
                marker = default_marker
                marker_class = default_marker_class
            result.append(f'<div class="ox-item{" fragment" if sequential else ""}"><span class="ox-marker {marker_class}"{editable_attrs(item_edit_id + ".marker")}>{marker}</span><span class="ox-text"{editable_attrs(item_edit_id + ".text")}>{text}</span></div>')
            continue

        if isinstance(item, str):
            result.append(f"<{tag}{cls_attr}{editable_attrs(item_edit_id)}>{item}</{tag}>")
        elif isinstance(item, dict):
            # 아이콘 불릿 지원: {"icon": "💡", "text": "내용"}
            if 'icon' in item and 'text' in item:
                icon = item['icon']
                text = item['text']
                result.append(f'<li class="icon-bullet{" fragment" if sequential else ""}"><span class="bullet-icon">{icon}</span><span class="bullet-text"{editable_attrs(item_edit_id + ".text")}>{text}</span></li>')
            elif tag == 'li':
                title = item.get('title', item.get('label', ''))
                desc = item.get('desc', item.get('text', ''))
                if title or desc:
                    result.append(f'''<li class="{"fragment" if sequential else ""}">
                        {f'<strong{editable_attrs(item_edit_id + ".title")}>{title}</strong>' if title else ''}
                        {f'<span{editable_attrs(item_edit_id + ".desc")}>{desc}</span>' if desc else ''}
                    </li>''')
            # 복합 객체 처리
            elif tag == 'timeline-item':
                date = item.get('date', '')
                date_html = f'<div class="timeline-date"{editable_attrs(item_edit_id + ".date")}>{date}</div>' if date else ''
                result.append(f'''<div class="timeline-item">
                    <div class="timeline-marker"><span>{index + 1}</span></div>
                    <div class="timeline-content">
                        {date_html}
                        <div class="timeline-title"{editable_attrs(item_edit_id + ".title")}>{item.get('title', '')}</div>
                        <div class="timeline-desc"{editable_attrs(item_edit_id + ".desc")}>{item.get('desc', '')}</div>
                    </div>
                </div>''')
            elif tag == 'stat-item':
                value_str = item.get('value', '')
                label_str = item.get('label', '')
                percentage = extract_percentage(value_str)
                # 수치가 0%인 텍스트인 경우, 클릭 시 100% 차오르게 기본 타겟을 100으로 설정
                target_percent = percentage if percentage > 0 else 100
                result.append(f'''<div class="card stat-card-button" onclick="clickStatCard(this, {target_percent})" style="text-align: center; display: flex; flex-direction: column; justify-content: space-between; padding: 1.2em 1em; cursor: pointer; transition: all 0.2s ease; flex: 1; max-width: 350px; min-width: 220px;">
                    <div class="stat-number"{editable_attrs(item_edit_id + ".value")} style="color: var(--color-accent); font-size: 1.8em; font-weight: 900; line-height: 1.1; margin-bottom: 0.1em;">{value_str}</div>
                    <div class="stat-label"{editable_attrs(item_edit_id + ".label")} style="font-size: 0.8em; color: var(--color-text-secondary); font-weight: 500; margin-bottom: 0.6em; word-break: keep-all;">{label_str}</div>
                    <div class="stat-gauge-container" style="background: rgba(0,0,0,0.05); border-radius: 4px; height: 8px; overflow: hidden; width: 100%; margin-top: auto;">
                        <div class="stat-gauge-bar" data-target-width="{percentage}%" style="background: var(--color-gradient); height: 100%; width: 0%; border-radius: 4px; transition: width 1.2s cubic-bezier(0.1, 0.8, 0.3, 1);"></div>
                    </div>
                </div>''')
            elif tag == 'quiz-option':
                result.append(f'<div class="quiz-option card"{editable_attrs(item_edit_id + ".text")}>{item.get("text", "")}</div>')
            # matrix 아이템: {"label": "텍스트", "quadrant": 1~4}
            elif tag == 'matrix-item':
                label = item.get('label', item.get('title', ''))
                icon = item.get('icon', '')
                desc = item.get('desc', '')
                icon_html = f'<div class="matrix-icon">{icon}</div>' if icon else ''
                desc_html = f'<div class="matrix-desc"{editable_attrs(item_edit_id + ".desc")}>{desc}</div>' if desc else ''
                result.append(f'<div class="matrix-cell card{" fragment" if sequential else ""}">{icon_html}<div class="matrix-label"{editable_attrs(item_edit_id + ".label")}>{label}</div>{desc_html}</div>')
    return "\n".join(result)


def render_bottom_takeaway(slide_data: dict) -> str:
    """BOTTOM_TAKEAWAY가 있으면 하단 요약 바 HTML을 생성합니다."""
    takeaway = slide_data.get('BOTTOM_TAKEAWAY', '')
    if not takeaway:
        return ''
    return f'''<div class="bottom-takeaway-bar">
    <div class="takeaway-content"{editable_attrs("BOTTOM_TAKEAWAY")}>{takeaway}</div>
</div>'''


def render_section_header(slide_data: dict) -> str:
    """SECTION_HEADER가 있으면 상단에 현재 섹션명을 표시합니다."""
    header = slide_data.get('SECTION_HEADER', '')
    if not header:
        return ''
    return f'<div class="section-header-tag"{editable_attrs("SECTION_HEADER")}>{header}</div>'


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
    if slide_type == 'text_image' and not data.get('CONTENT') and data.get('BODY'):
        data['CONTENT'] = data.get('BODY', '')
    if slide_type == 'image_comparison':
        if not data.get('LEFT_IMAGE_SRC') and data.get('LEFT_IMAGE'):
            data['LEFT_IMAGE_SRC'] = data.get('LEFT_IMAGE', '')
        if not data.get('RIGHT_IMAGE_SRC') and data.get('RIGHT_IMAGE'):
            data['RIGHT_IMAGE_SRC'] = data.get('RIGHT_IMAGE', '')
        if not data.get('LEFT_DESC') and data.get('LEFT_TITLE'):
            data['LEFT_DESC'] = data.get('LEFT_TITLE', '')
        if not data.get('RIGHT_DESC') and data.get('RIGHT_TITLE'):
            data['RIGHT_DESC'] = data.get('RIGHT_TITLE', '')
    if slide_type == 'quiz':
        if not data.get('QUIZ_OPTIONS') and data.get('OPTIONS'):
            data['QUIZ_OPTIONS'] = data.get('OPTIONS', [])
        if data.get('ANSWER') and 'ANSWER_INDEX' not in data and data.get('QUIZ_OPTIONS'):
            for idx, option in enumerate(data.get('QUIZ_OPTIONS', [])):
                option_text = option.get('text', option) if isinstance(option, dict) else option
                if str(option_text).strip() == str(data.get('ANSWER')).strip():
                    data['ANSWER_INDEX'] = idx
                    break
    if slide_type == 'closing' and not data.get('MESSAGE') and data.get('SUBTITLE'):
        data['MESSAGE'] = data.get('SUBTITLE', '')
    if slide_type == 'tutorial':
        raw_title = str(data.get('TITLE', ''))
        data['DISPLAY_TITLE'] = re.sub(r'^\s*\d+\s*단계\s*[:：;；]\s*', '', raw_title)
    elif 'TITLE' in data:
        data['DISPLAY_TITLE'] = data.get('TITLE', '')

    if slide_type == 'vs_ox' or 'O_ITEMS' in data or 'X_ITEMS' in data:
        data['O_MARKER'] = str(get_first_value(data, ['O_MARKER', 'o_marker'], '⭕'))
        data['X_MARKER'] = str(get_first_value(data, ['X_MARKER', 'x_marker'], '❌'))

    if 'BULLET_ITEMS' in data:
        data['BULLET_ITEMS'] = process_list(data['BULLET_ITEMS'], 'li', edit_key='BULLET_ITEMS', sequential=data.get('SEQUENTIAL', False))

    if 'LEFT_ITEMS' in data:
        data['LEFT_ITEMS'] = process_list(data['LEFT_ITEMS'], 'li', edit_key='LEFT_ITEMS', sequential=data.get('SEQUENTIAL', False))

    if 'RIGHT_ITEMS' in data:
        data['RIGHT_ITEMS'] = process_list(data['RIGHT_ITEMS'], 'li', edit_key='RIGHT_ITEMS', sequential=data.get('SEQUENTIAL', False))

    if 'SUMMARY_ITEMS' in data:
        data['SUMMARY_ITEMS'] = process_list(data['SUMMARY_ITEMS'], 'li', edit_key='SUMMARY_ITEMS', sequential=data.get('SEQUENTIAL', False))

    if 'TIMELINE_ITEMS' in data:
        timeline_count = len(data['TIMELINE_ITEMS']) if isinstance(data['TIMELINE_ITEMS'], list) else 0
        data['TIMELINE_DENSITY_CLASS'] = 'timeline-rail' if timeline_count <= 4 else 'timeline-compact'
        data['TIMELINE_ITEMS'] = process_list(data['TIMELINE_ITEMS'], 'timeline-item', edit_key='TIMELINE_ITEMS', sequential=data.get('SEQUENTIAL', False))

    if 'STAT_ITEMS' in data:
        data['STAT_ITEMS'] = process_list(data['STAT_ITEMS'], 'stat-item', edit_key='STAT_ITEMS', sequential=data.get('SEQUENTIAL', False))

    if 'QUIZ_OPTIONS' in data:
        answer_index = data.get('ANSWER_INDEX', 0)
        quiz_options = data['QUIZ_OPTIONS']
        options_html_parts = []
        for i, option in enumerate(quiz_options):
            option_text = option.get('text', option) if isinstance(option, dict) else option
            is_correct = "true" if i == answer_index else "false"
            options_html_parts.append(f'''<div class="quiz-option card button-type" onclick="checkQuizAnswer(this, {is_correct})" style="cursor: pointer; transition: all 0.2s ease; margin-bottom: 0.3em; padding: 0.6em 1em; text-align: center; display: flex; align-items: center; justify-content: center; gap: 0.8em; border-radius: 12px; background: var(--color-card-bg); border: 1px solid var(--color-card-border); box-shadow: 0 4px 12px rgba(0,0,0,0.03); font-size: 0.8em;">
                <span class="option-marker" style="display: inline-flex; align-items: center; justify-content: center; width: 1.8em; height: 1.8em; border-radius: 50%; background: rgba(0,0,0,0.05); font-weight: 700; font-size: 0.85em; flex-shrink: 0; transition: background 0.2s ease, color 0.2s ease;">{chr(65+i)}</span>
                <span class="option-text"{editable_attrs(f'QUIZ_OPTIONS[{i}].text')} style="word-break: keep-all; font-weight: 500; line-height: 1.3; text-align: center;">{option_text}</span>
            </div>''')
        data['QUIZ_OPTIONS'] = '\n'.join(options_html_parts)

    # 신규: 매트릭스 아이템
    if 'MATRIX_ITEMS' in data:
        data['MATRIX_ITEMS'] = process_list(data['MATRIX_ITEMS'], 'matrix-item', edit_key='MATRIX_ITEMS', sequential=data.get('SEQUENTIAL', False))

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
        for item in data['O_ITEMS']:
            if isinstance(item, dict):
                if not item.get('marker'):
                    item['marker'] = data['O_MARKER']
                if not item.get('marker_class'):
                    item['marker_class'] = 'marker-o'
        data['O_ITEMS'] = process_list(data['O_ITEMS'], 'ox-item', edit_key='O_ITEMS', default_marker=data['O_MARKER'], default_marker_class='marker-o', sequential=data.get('SEQUENTIAL', False))
    if 'X_ITEMS' in data:
        for item in data['X_ITEMS']:
            if isinstance(item, dict):
                if not item.get('marker'):
                    item['marker'] = data['X_MARKER']
                if not item.get('marker_class'):
                    item['marker_class'] = 'marker-x'
        data['X_ITEMS'] = process_list(data['X_ITEMS'], 'ox-item', edit_key='X_ITEMS', default_marker=data['X_MARKER'], default_marker_class='marker-x', sequential=data.get('SEQUENTIAL', False))

    # 신규: 로드맵 아이템
    if 'ROADMAP_ITEMS' in data:
        roadmap_items = data['ROADMAP_ITEMS']
        roadmap_html_parts = []
        for i, item in enumerate(roadmap_items):
            if isinstance(item, dict):
                label = item.get('label', f'Step {i+1}')
                desc = item.get('desc', '')
                desc_html = f'<div class="roadmap-desc"{editable_attrs(f"ROADMAP_ITEMS[{i}].desc")}>{desc}</div>' if desc else ''
                roadmap_html_parts.append(f'''<div class="roadmap-step">
                    <div class="roadmap-num">{i+1}</div>
                    <div class="roadmap-label"{editable_attrs(f"ROADMAP_ITEMS[{i}].label")}>{label}</div>
                    {desc_html}
                </div>''')
            else:
                roadmap_html_parts.append(f'''<div class="roadmap-step">
                    <div class="roadmap-num">{i+1}</div>
                    <div class="roadmap-label"{editable_attrs(f"ROADMAP_ITEMS[{i}]")}>{item}</div>
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
    html_keys = {'QUIZ_OPTIONS', 'ROADMAP_ITEMS', 'STEPPER_ITEMS', 'TIMELINE_ITEMS', 'MATRIX_ITEMS', 'BULLET_ITEMS', 'LEFT_ITEMS', 'RIGHT_ITEMS', 'SUMMARY_ITEMS', 'STAT_ITEMS', 'O_ITEMS', 'X_ITEMS', 'BOTTOM_TAKEAWAY_HTML', 'SECTION_HEADER_HTML'}
    for key, value in data.items():
        if isinstance(value, str) and key not in html_keys:
            value = value.replace('\n', '<br>')
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

    html = apply_style_overrides(html, data.get('STYLE_OVERRIDES', {}))

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
    for idx, slide in enumerate(slides_data):
        slide['SLIDE_INDEX'] = idx
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
    
    # 슬라이드 본문을 먼저 조립해야, 내부의 클래스(screenshot-frame 등)에 동적 테마 치환이 적용됩니다!
    final_html = final_html.replace('{{SLIDES_CONTENT}}', slides_content)
    
    # 테마 에디터와 충돌하지 않도록 모든 프리셋, 패턴, 장식 클래스를 문자열 치환 주입
    if theme_colors:
        frame_preset = theme_colors.get('image_frame_preset', 'business')
        card_preset = theme_colors.get('card_style_preset', 'business_clean')
        icon_preset = theme_colors.get('icon_preset', 'business')
        font_preset = theme_colors.get('font_preset', 'friendly')
        highlight_preset = theme_colors.get('highlight_style', theme_colors.get('strong_style', 'friendly'))
        takeaway_preset = theme_colors.get('takeaway_style', 'friendly')
        motion_preset = theme_colors.get('motion_preset', 'friendly')

        # reveal 기본 컨테이너에 모든 프리셋 클래스 주입
        reveal_classes = f"reveal card-preset-{card_preset} icon-preset-{icon_preset} theme-{font_preset} highlight-{highlight_preset} takeaway-{takeaway_preset} motion-{motion_preset}"
        final_html = final_html.replace('class="reveal"', f'class="{reveal_classes}"')

        # 이미지 프레임 클래스 주입
        final_html = final_html.replace('class="screenshot-frame ', f'class="screenshot-frame frame-{frame_preset} ')
        final_html = final_html.replace('class="screenshot-frame"', f'class="screenshot-frame frame-{frame_preset}"')
        
        # 배경 패턴 주입
        pattern_preset = theme_colors.get('bg_pattern_style', 'none')
        if pattern_preset != 'none':
            final_html = final_html.replace('class="pattern-overlay"', f'class="pattern-overlay pattern-{pattern_preset}"')
        
        # 배경 장식 주입
        decorations = theme_colors.get('decorations', [])
        if decorations:
            if 'corner_accent' in decorations:
                final_html = final_html.replace('class="decor-corner ', 'class="decor-corner active ')
            if 'circles' in decorations:
                final_html = final_html.replace('class="decor-circle ', 'class="decor-circle active ')
            if 'hud_brackets' in decorations:
                final_html = final_html.replace('class="decor-hud ', 'class="decor-hud active ')
            if 'wavy_line' in decorations:
                final_html = final_html.replace('class="decor-wavy"', 'class="decor-wavy active"')
            if 'geometric_shapes' in decorations:
                final_html = final_html.replace('class="decor-shape ', 'class="decor-shape active ')
            if 'tech_grid_lines' in decorations:
                final_html = final_html.replace('class="decor-techlines"', 'class="decor-techlines active"')

    assert_no_unresolved_includes(final_html)

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
