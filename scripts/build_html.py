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

    frame_preset = theme_colors.get('image_frame_preset', 'business')
    card_preset = theme_colors.get('card_style_preset', 'business_clean')
    icon_preset = theme_colors.get('icon_preset', 'business')
    highlight_preset = theme_colors.get('highlight_style', theme_colors.get('strong_style', 'friendly'))
    takeaway_preset = theme_colors.get('takeaway_style', 'friendly')
    motion_preset = theme_colors.get('motion_preset', 'friendly')

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


def normalize_youtube_url(url: str) -> dict:
    """YouTube URL을 정규화하여 video_id와 embed_url, thumbnail_url 등을 반환합니다."""
    if not url:
        return {}
        
    import re
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:\?|&|$)'
    match = re.search(pattern, url)
    if not match:
        pattern2 = r'youtu\.be\/([0-9A-Za-z_-]{11})'
        match = re.search(pattern2, url)
        
    if not match:
        return {}
        
    video_id = match.group(1)
    return {
        'source_url': url,
        'video_id': video_id,
        'embed_url': f"https://www.youtube.com/embed/{video_id}",
        'watch_url': f"https://www.youtube.com/watch?v={video_id}",
        'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    }


def extract_percentage(value_str: str) -> int:
    """수치 텍스트로부터 게이지 바에 채울 백분율 값을 추출합니다."""
    import re
    if '%' in value_str:
        match = re.search(r'([\d\.]+)', value_str)
        if match:
            try:
                return int(float(match.group(1)))
            except ValueError:
                pass
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


def format_minutes(value) -> str:
    text = str(value).strip()
    if not text:
        return ''
    return text if text.endswith('분') else f'{text}분'


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


def tag_page_section(html: str, page_type: str, page_index: int) -> str:
    """Reveal section에 원본 page 인덱스를 심어 에디터 저장 대상을 안정화합니다."""
    attrs = f' data-page-type="{escape(page_type, quote=True)}" data-page-index="{page_index}"'
    return re.sub(r'<section\b', f'<section{attrs}', html, count=1)


def render_ox_reveal_items(items) -> str:
    if not isinstance(items, list):
        return ''

    rows = []
    for index, item in enumerate(items):
        if isinstance(item, dict):
            statement = item.get('statement', item.get('text', ''))
            answer = item.get('answer', '')
            explanation = item.get('explanation', '')
        else:
            statement = str(item)
            answer = ''
            explanation = ''

        explanation_html = ''
        if explanation:
            explanation_html = f'<div class="ox-reveal-explanation fragment"{editable_attrs(f"ITEMS[{index}].explanation")}>{explanation}</div>'

        rows.append(f'''<div class="ox-reveal-row">
            <div class="ox-reveal-statement"><span class="ox-reveal-num">{index + 1}</span><span{editable_attrs(f"ITEMS[{index}].statement")}>{statement}</span></div>
            <div class="ox-reveal-answer fragment"{editable_attrs(f"ITEMS[{index}].answer")}>{answer}</div>
            {explanation_html}
        </div>''')
    return '\n'.join(rows)


def render_answer_key_block(block: dict, block_index: int, q_idx: int, prefix: str) -> str:
    block_type = block.get('block_type', 'short_answer')
    title = block.get('title', f'활동 {q_idx}')
    
    header = f'<h3 class="answer-key-block-title"{editable_attrs(f"{prefix}.title")}><span class="q-num" style="color:var(--color-accent); margin-right: 8px;">{q_idx}.</span>{title}</h3>'
    
    content = ""
    if block_type == 'ox_check':
        items = block.get('items', [])
        lines = []
        for i, item in enumerate(items):
            ans = item.get('answer', '') if isinstance(item, dict) else ''
            exp = item.get('explanation', '') if isinstance(item, dict) else ''
            lines.append(f"<div>{i+1}. <strong>{ans}</strong> {f'- {exp}' if exp else ''}</div>")
        content = "".join(lines)
    
    elif block_type == 'short_answer':
        ans = block.get('sample_answer', '예시 답안 없음')
        content = f"<div>정답(예시): {ans}</div>"
        
    elif block_type == 'cloze_word_bank':
        sentences = block.get('sentences', [])
        answers = []
        for s in sentences:
            if isinstance(s, dict) and 'answer' in s:
                answers.append(s['answer'])
        ans_str = ", ".join(answers)
        content = f"<div>정답: {ans_str}</div>"
        
    elif block_type == 'matching_lines':
        pairs = block.get('pairs', [])
        lines = []
        for i, p in enumerate(pairs):
            if not isinstance(p, dict):
                continue
            left = escape(str(p.get('left', '')))
            right = escape(str(p.get('right', '')))
            lines.append(
                f'<div class="answer-key-match-row">'
                f'<span class="answer-key-match-num">{i + 1}</span>'
                f'<span class="answer-key-match-left">{left}</span>'
                f'<span class="answer-key-match-arrow">→</span>'
                f'<strong class="answer-key-match-right">{right}</strong>'
                f'</div>'
            )
        content = "".join(lines) or "<div>표시할 정답 쌍이 없습니다.</div>"
        
    elif block_type == 'table_fill':
        rows = block.get('rows', [])
        lines = []
        for r in rows:
            if len(r) >= 2:
                left = r[0].get('text', r[0]) if isinstance(r[0], dict) else str(r[0])
                right = r[1].get('text', r[1]) if isinstance(r[1], dict) else str(r[1])
                lines.append(f"<div>{left}: {right}</div>")
        content = "".join(lines)
        
    elif block_type == 'reflection_checklist':
        content = "<div style='color:#64748b;'>자기점검 문항이므로 정답이 없습니다. 순회지도 시 참고용으로 활용하세요.</div>"
        
    return f'<div class="answer-key-block">{header}<div class="answer-key-content">{content}</div></div>'


def render_worksheet_block(block: dict, block_index: int, q_idx: int, answer_key: bool = False) -> str:
    block_type = block.get('block_type', 'short_answer')
    title = block.get('title', f'활동 {q_idx}')
    instruction = block.get('instruction', block.get('prompt', ''))
    prefix = block.get('_original_path', f'blocks[{block_index}]')
    header = f'''<div class="worksheet-block-header">
        <h2{editable_attrs(f"{prefix}.title")}><span class="q-num" style="color:var(--color-accent); margin-right: 8px;">{q_idx}.</span>{title}</h2>
        {f'<p{editable_attrs(f"{prefix}.instruction")}>{instruction}</p>' if instruction else ''}
    </div>'''

    if block_type == 'ox_check':
        items = block.get('items', [])
        item_rows = []
        for item_index, item in enumerate(items):
            statement = item.get('statement', item.get('text', '')) if isinstance(item, dict) else str(item)
            answer = item.get('answer', '') if isinstance(item, dict) else ''
            explanation = item.get('explanation', '') if isinstance(item, dict) else ''
            if answer_key:
                right = f'<strong>{answer}</strong>{f" - {explanation}" if explanation else ""}'
            else:
                right = '<span class="worksheet-ox-choice">O</span><span class="worksheet-ox-choice">X</span>'
            item_rows.append(f'''<li>
                <span class="worksheet-question"{editable_attrs(f"{prefix}.items[{item_index}].statement")}>{statement}</span>
                <span class="worksheet-answer-slot">{right}</span>
            </li>''')
        return f'<div class="worksheet-block worksheet-block-ox">{header}<ol>{''.join(item_rows)}</ol></div>'

    if block_type == 'short_answer':
        lines = int(block.get('answer_lines', 2) or 2)
        answer_lines = ''.join('<div class="worksheet-answer-line"></div>' for _ in range(max(1, min(lines, 6))))
        if answer_key and block.get('sample_answer'):
            answer_lines = f'<div class="worksheet-sample-answer"{editable_attrs(f"{prefix}.sample_answer")}>{block.get("sample_answer")}</div>'
        return f'<div class="worksheet-block worksheet-block-short-answer">{header}{answer_lines}</div>'

    if block_type == 'cloze_word_bank':
        word_bank = block.get('word_bank', [])
        sentences = block.get('sentences', [])
        wb_html = ' '.join(f'<span class="cloze-word"{editable_attrs(f"{prefix}.word_bank[{i}]")}>{w}</span>' for i, w in enumerate(word_bank))
        sent_html = []
        for i, s in enumerate(sentences):
            text = str(s.get('text', s)) if isinstance(s, dict) else str(s)
            import re
            if answer_key:
                ans = s.get('answer', '') if isinstance(s, dict) else ''
                if ans:
                    text = text.replace('[    ]', f'[ <strong style="color: var(--color-accent);">{ans}</strong> ]')
                else:
                    text = re.sub(r'\[(.*?)\]', r'[ <strong style="color: var(--color-accent);">\1</strong> ]', text)
            else:
                text = text.replace('[    ]', '<span class="cloze-blank"></span>')
                text = re.sub(r'\[(.*?)\]', '<span class="cloze-blank"></span>', text)
            sent_html.append(f'<li{editable_attrs(f"{prefix}.sentences[{i}].text")}>{text}</li>')
        return f'<div class="worksheet-block worksheet-block-cloze">{header}<div class="word-bank-box">{wb_html}</div><ol class="cloze-sentences">{"".join(sent_html)}</ol></div>'

    if block_type == 'matching_lines':
        pairs = block.get('pairs', [])
        import random
        # 슬라이드와 동일한 시드 사용 (슬라이드는 TITLE = "{title} 정답 확인" 으로 시드)
        slide_seed = f'{title} 정답 확인'
        random.seed(slide_seed)
        right_items = [{"id": i, "text": p.get('right', '')} for i, p in enumerate(pairs)]
        random.shuffle(right_items)
        
        n = len(pairs)
        id_prefix = 'ak' if answer_key else 'ws'
        ws_id = f'{id_prefix}-match-{block_index}'
        
        left_col = []
        right_col = []
        svg_lines = []
        for i, p in enumerate(pairs):
            left_dot_id = f'{ws_id}-ld-{i}'
            right_dot_id = f'{ws_id}-rd-{i}'
            left_col.append(f'<div class="match-item-box" id="{ws_id}-l-{i}"><div class="match-left"{editable_attrs(f"{prefix}.pairs[{i}].left")}>{p.get("left", "")}</div><div class="match-dot" id="{left_dot_id}"></div></div>')
            # 슬라이드와 완전히 동일한 SVG 구조 (fragment 클래스만 제거 → 애니메이션 없이 즉시 표시)
            if answer_key:
                svg_lines.append(f'<g class="ws-match-line" data-start="#{left_dot_id}" data-end="#{right_dot_id}"><path class="match-svg-line" fill="none" stroke="var(--color-accent)" stroke-width="4" stroke-linecap="round" stroke-opacity="0.85" /><polygon class="match-svg-arrowhead" fill="var(--color-accent)" opacity="0.85" /></g>')
        for r in right_items:
            i = r["id"]
            right_col.append(f'<div class="match-item-box" id="{ws_id}-r-{i}"><div class="match-dot" id="{ws_id}-rd-{i}"></div><div class="match-right"{editable_attrs(f"{prefix}.pairs[{i}].right")}>{r["text"]}</div></div>')
            
        answer_svg = ''
        if answer_key:
            answer_svg = f'<svg class="match-svg-overlay match-answer-svg" style="position: absolute; top:0; left:0; width: 100%; height: 100%; z-index: 10; pointer-events: none; overflow: visible;">{"".join(svg_lines)}</svg>'
        
        return f'<div class="worksheet-block worksheet-block-matching">{header}<div class="matching-columns-container" id="{ws_id}" style="position: relative; display: flex; justify-content: space-between; flex: 1; min-height: 0; align-items: stretch;">{answer_svg}<div class="match-col match-col-left" style="display: flex; flex-direction: column; justify-content: space-around; z-index: 2; width: 45%; gap:20px;">{"".join(left_col)}</div><div class="match-col match-col-right" style="display: flex; flex-direction: column; justify-content: space-around; z-index: 2; width: 45%; gap:20px;">{"".join(right_col)}</div></div></div>'

    if block_type == 'table_fill':
        headers = block.get('headers', [])
        rows = block.get('rows', [])
        th_html = ''.join(f'<th{editable_attrs(f"{prefix}.headers[{i}]")}>{h}</th>' for i, h in enumerate(headers))
        tr_html = []
        for r_idx, r in enumerate(rows):
            td_html = []
            for c_idx, cell in enumerate(r):
                text = str(cell.get('text', cell)) if isinstance(cell, dict) else str(cell)
                is_blank = cell.get('is_blank', False) if isinstance(cell, dict) else (c_idx > 0)
                if is_blank:
                    if answer_key:
                        td_html.append(f'<td class="blank-cell answered"><strong>{text}</strong></td>')
                    else:
                        td_html.append(f'<td class="blank-cell"></td>')
                else:
                    path = f"{prefix}.rows[{r_idx}][{c_idx}]" if not isinstance(cell, dict) else f"{prefix}.rows[{r_idx}][{c_idx}].text"
                    td_html.append(f'<td{editable_attrs(path)}>{text}</td>')
            tr_html.append(f'<tr>{"".join(td_html)}</tr>')
        return f'<div class="worksheet-block worksheet-block-table">{header}<table class="worksheet-table"><thead><tr>{th_html}</tr></thead><tbody>{"".join(tr_html)}</tbody></table></div>'

    if block_type == 'reflection_checklist':
        items = block.get('items', [])
        chk_html = []
        for i, item in enumerate(items):
            text = str(item.get('text', item)) if isinstance(item, dict) else str(item)
            chk_html.append(f'<li><div class="check-box"></div><span{editable_attrs(f"{prefix}.items[{i}].text")}>{text}</span></li>')
        return f'<div class="worksheet-block worksheet-block-reflection">{header}<ul class="reflection-list">{"".join(chk_html)}</ul></div>'

    # ponytail: unsupported blocks keep their data visible; add custom renderers when real lessons need them.
    return f'<div class="worksheet-block worksheet-block-placeholder">{header}<div class="worksheet-placeholder">{block_type}</div></div>'


def render_worksheet_page(page: dict, page_index: int, page_type: str = 'worksheet') -> str:
    title = page.get('title', page.get('TITLE', '학습지'))
    blocks = page.get('blocks', page.get('BLOCKS', []))
    start_q_idx = page.get('start_q_idx', 1)
    answer_key = page_type == 'answer_key'
    
    if answer_key:
        rendered_blocks = '\n'.join(render_worksheet_block(block, idx, start_q_idx + idx, answer_key=True) for idx, block in enumerate(blocks))
        label = '교사용 정답지'
        header_html = f'''<header class="worksheet-page-header">
            <div class="worksheet-page-label">{label}</div>
            <h1{editable_attrs("title")}>{title}</h1>
        </header>'''
    else:
        rendered_blocks = '\n'.join(render_worksheet_block(block, idx, start_q_idx + idx) for idx, block in enumerate(blocks))
        label = '학생용 활동지'
        header_html = f'''<header class="worksheet-page-header">
            <div class="worksheet-page-label">{label}</div>
            <h1{editable_attrs("title")}>{title}</h1>
            <div class="worksheet-student-info">
                <span class="info-box">학년 반 번 이름: __________________</span>
                <span class="info-box">날짜: 20___년 ___월 ___일</span>
            </div>
        </header>'''

    html = f'''<section class="worksheet-section">
        <div class="worksheet-page {'answer-key-page' if answer_key else ''}">
            {header_html}
            <main class="worksheet-page-body">
                {rendered_blocks}
            </main>
        </div>
    </section>'''
    html = apply_style_overrides(html, page.get('STYLE_OVERRIDES', {}))
    return tag_page_section(html, page_type, page_index)


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

    if slide_type == 'activity_instruction':
        data['WORKSHEET_REF'] = get_first_value(data, ['WORKSHEET_REF', 'worksheet_ref'], '학습지')
        data['TIMER_MINUTES'] = format_minutes(get_first_value(data, ['TIMER_MINUTES', 'timer_minutes'], ''))
        data['THINK_QUESTION'] = get_first_value(data, ['THINK_QUESTION', 'think_question'], '')
        if not data.get('INSTRUCTION') and data.get('instruction'):
            data['INSTRUCTION'] = data.get('instruction', '')

    if slide_type == 'ox_reveal':
        items = data.get('ITEMS', data.get('OX_ITEMS', data.get('items', [])))
        data['OX_REVEAL_ITEMS'] = render_ox_reveal_items(items)

    if slide_type == 'sample_answer_reveal':
        data['PROMPT'] = data.get('PROMPT', data.get('prompt', ''))
        data['SAMPLE_ANSWER'] = data.get('SAMPLE_ANSWER', data.get('sample_answer', ''))

    if slide_type == 'cloze_reveal':
        wb = data.get('WORD_BANK', data.get('word_bank', []))
        data['WORD_BANK_HTML'] = ''.join(
            f'<span class="cloze-word cloze-wb-word"{editable_attrs(f"WORD_BANK[{i}]")} data-word="{escape(str(w), quote=True)}">{w}</span>'
            for i, w in enumerate(wb)
        )
        items = data.get('ITEMS', data.get('sentences', []))
        rows = []
        for i, item in enumerate(items):
            text_val = str(item.get('text', item)) if isinstance(item, dict) else str(item)
            ans = str(item.get('answer', '')) if isinstance(item, dict) else ''

            def render_cloze_blank(match):
                word = match.group(1).strip() or ans
                if not word:
                    return match.group(0)
                word_attr = escape(str(word), quote=True)
                return f'<span class="cloze-blank-reveal fragment js-cloze-anim" data-word="{word_attr}" >{word}</span>'

            text_html = re.sub(r'\[([^\]]*)\]', render_cloze_blank, text_val)
            rows.append(f'<div class="cloze-reveal-row"{editable_attrs(f"ITEMS[{i}].text")}>{text_html}</div>')
        data['CLOZE_REVEAL_ITEMS'] = '\n'.join(rows)

    if slide_type == 'matching_reveal':
        pairs = data.get('PAIRS', data.get('pairs', []))
        import random
        seed_str = data.get('TITLE', 'matching')
        random.seed(seed_str)
        right_items = [{"id": i, "text": p.get('right', '')} for i, p in enumerate(pairs)]
        random.shuffle(right_items)
        left_col = []
        right_col = []
        svg_lines = []
        block_id = data.get('SLIDE_INDEX', 0)
        for i, p in enumerate(pairs):
            left_dot_id = f'slide-match-l-dot-{block_id}-{i}'
            right_dot_id = f'slide-match-r-dot-{block_id}-{i}'
            left_col.append(f'<div class="match-item-box" id="slide-match-l-{block_id}-{i}"><div class="match-left"{editable_attrs(f"PAIRS[{i}].left")}>{p.get("left", "")}</div><div class="match-dot" id="{left_dot_id}"></div></div>')
            svg_lines.append(f'<g class="fragment js-match-anim" data-start="#{left_dot_id}" data-end="#{right_dot_id}"><path class="match-svg-line" fill="none" stroke="var(--color-accent)" stroke-width="6" stroke-linecap="round" stroke-opacity="0.9" /><polygon class="match-svg-arrowhead" fill="var(--color-accent)" opacity="0.9" /></g>')
        
        for r in right_items:
            i_r = r["id"]
            right_col.append(f'<div class="match-item-box" id="slide-match-r-{block_id}-{i_r}"><div class="match-dot" id="slide-match-r-dot-{block_id}-{i_r}"></div><div class="match-right"{editable_attrs(f"PAIRS[{i_r}].right")}>{r["text"]}</div></div>')
            
        data['MATCHING_REVEAL_ITEMS'] = f'''<div class="matching-columns-container" style="position: relative; display: flex; justify-content: space-between; width: 100%; min-height: 350px;">
            <div class="match-col match-col-left" style="display: flex; flex-direction: column; justify-content: space-around; z-index: 2; width: 45%; gap:20px;">{"".join(left_col)}</div>
            <svg class="match-svg-overlay" style="position: absolute; top:0; left:0; width: 100%; height: 100%; z-index: 10; pointer-events: none;">{"".join(svg_lines)}</svg>
            <div class="match-col match-col-right" style="display: flex; flex-direction: column; justify-content: space-around; z-index: 2; width: 45%; gap:20px;">{"".join(right_col)}</div>
        </div>'''

    if slide_type == 'table_answer_reveal':
        headers = data.get('HEADERS', data.get('headers', []))
        rows_data = data.get('ROWS', data.get('rows', []))
        th_html = ''.join(f'<th{editable_attrs(f"HEADERS[{i}]")}>{h}</th>' for i, h in enumerate(headers))
        tr_html = []
        for r_i, r in enumerate(rows_data):
            td_html = []
            for cell_index, cell in enumerate(r):
                text = str(cell.get('text', cell)) if isinstance(cell, dict) else str(cell)
                path = f"ROWS[{r_i}][{cell_index}].text" if isinstance(cell, dict) else f"ROWS[{r_i}][{cell_index}]"
                if (isinstance(cell, dict) and cell.get('is_blank')) or cell_index > 0:
                    td_html.append(f'<td class="blank-cell"><div class="fragment pop-glow-reveal"{editable_attrs(path)} style="color: var(--color-accent); font-weight: bold;">{text}</div></td>')
                else:
                    td_html.append(f'<td{editable_attrs(path)}>{text}</td>')
            tr_html.append(f'<tr>{"".join(td_html)}</tr>')
        data['TABLE_REVEAL_HTML'] = f'<table class="reveal-table" style="width: 100%; border-collapse: collapse;"><thead><tr>{th_html}</tr></thead><tbody>{"".join(tr_html)}</tbody></table>'

    if slide_type == 'share_prompt':
        data['INSTRUCTION'] = data.get('INSTRUCTION', data.get('instruction', '생각을 나눠 봅시다.'))
        questions = data.get('QUESTIONS', data.get('questions', []))
        q_html = []
        for i, q in enumerate(questions):
            q_html.append(f'<div class="share-question fragment">{q}</div>')
        data['SHARE_QUESTIONS_HTML'] = '\n'.join(q_html)

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
    html_keys = {'QUIZ_OPTIONS', 'ROADMAP_ITEMS', 'STEPPER_ITEMS', 'TIMELINE_ITEMS', 'MATRIX_ITEMS', 'BULLET_ITEMS', 'LEFT_ITEMS', 'RIGHT_ITEMS', 'SUMMARY_ITEMS', 'STAT_ITEMS', 'O_ITEMS', 'X_ITEMS', 'OX_REVEAL_ITEMS', 'BOTTOM_TAKEAWAY_HTML', 'SECTION_HEADER_HTML', 'CLOZE_REVEAL_ITEMS', 'MATCHING_REVEAL_ITEMS', 'TABLE_REVEAL_HTML', 'WORD_BANK_HTML', 'SHARE_QUESTIONS_HTML'}
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

    # 에디터 모드 등에서 참조할 수 있도록 실제 레이아웃 이름 주입
    html = re.sub(r'(<section[^>]*)(>)', rf'\1 data-layout-name="{slide_type}"\2', html, count=1)

    return html


def normalize_pages(plan: dict) -> list:
    if isinstance(plan.get('pages'), list) and plan['pages']:
        return plan['pages']
    pages = [
        {**slide, 'page_type': 'slide', 'size': '16:9', 'layout': slide.get('layout', slide.get('type', 'title'))}
        for slide in plan.get('slides', [])
    ]
    packages = plan.get('activity_packages', [])
    if not isinstance(packages, list) or not packages:
        return pages

    worksheet_blocks = []
    for index, package in enumerate(packages):
        if not isinstance(package, dict):
            continue
        title = package.get('title', f'활동 {index + 1}')
        work_time = package.get('work_time_minutes', '')
        
        # 1. 미디어 슬라이드 처리 (활동 전에 삽입)
        media = package.get('media', {})
        if isinstance(media, dict) and media.get('enabled') and media.get('url'):
            media_info = normalize_youtube_url(media.get('url', ''))
            if media_info:
                layout = 'video_hook' if media.get('display_mode') == 'embed' else 'video_link_card'
                pages.append({
                    'page_type': 'slide',
                    'layout': layout,
                    'TITLE': media.get('title', '영상 자료'),
                    'VIDEO_ID': media_info.get('video_id'),
                    'EMBED_URL': media_info.get('embed_url'),
                    'THUMBNAIL_URL': media_info.get('thumbnail_url'),
                    'WATCH_URL': media_info.get('watch_url'),
                    'PURPOSE': media.get('purpose', ''),
                    'STUDENT_TASK': media.get('student_task', ''),
                    'SPEAKER_NOTES': '주의: 이 영상은 외부 YouTube 링크입니다. 수업 전에 재생 가능 여부를 확인하세요.\n\n원본 링크: ' + media.get('url', '')
                })
                
        # 2. 학생 활동 안내
        block = package.get('worksheet_block', {})
        if isinstance(block, dict) and block:
            block['_original_path'] = f'$root.activity_packages[{index}].worksheet_block'
            worksheet_blocks.append(block)

        pages.append({
            'page_type': 'slide',
            'layout': 'activity_instruction',
            'TITLE': title,
            'WORKSHEET_REF': f'학습지 {index + 1}번',
            'INSTRUCTION': package.get('student_task', f'{title}을(를) 풀어 봅시다.'),
            'TIMER_MINUTES': format_minutes(work_time),
            'THINK_QUESTION': package.get('think_question', '')
        })

        block_type = block.get('block_type')
        if block_type == 'ox_check':
            pages.append({
                'page_type': 'slide',
                'layout': 'ox_reveal',
                'TITLE': f'{title} 정답 확인',
                'ITEMS': block.get('items', []),
                'SPEAKER_NOTES': '\n'.join(package.get('teacher_prompt', []))
            })
        elif block_type == 'cloze_word_bank':
            pages.append({
                'page_type': 'slide',
                'layout': 'cloze_reveal',
                'TITLE': f'{title} 정답 확인',
                'WORD_BANK': block.get('word_bank', []),
                'ITEMS': block.get('sentences', []),
                'SPEAKER_NOTES': '\n'.join(package.get('teacher_prompt', []))
            })
        elif block_type == 'matching_lines':
            pages.append({
                'page_type': 'slide',
                'layout': 'matching_reveal',
                'TITLE': f'{title} 정답 확인',
                'PAIRS': block.get('pairs', []),
                'SPEAKER_NOTES': '\n'.join(package.get('teacher_prompt', []))
            })
        elif block_type == 'table_fill':
            pages.append({
                'page_type': 'slide',
                'layout': 'table_answer_reveal',
                'TITLE': f'{title} 정답 확인',
                'HEADERS': block.get('headers', []),
                'ROWS': block.get('rows', []),
                'SPEAKER_NOTES': '\n'.join(package.get('teacher_prompt', []))
            })
        elif block_type == 'reflection_checklist':
            pages.append({
                'page_type': 'slide',
                'layout': 'share_prompt',
                'TITLE': f'{title} 공유',
                'PROMPT': block.get('follow_up_prompt', '오늘 배운 내용을 한 문장으로 공유해 봅시다.'),
                'SPEAKER_NOTES': '\n'.join(package.get('teacher_prompt', []))
            })
        elif block_type == 'short_answer':
            pages.append({
                'page_type': 'slide',
                'layout': 'sample_answer_reveal',
                'TITLE': f'{title} 예시 답안',
                'PROMPT': block.get('instruction', ''),
                'SAMPLE_ANSWER': block.get('sample_answer', ''),
                'SPEAKER_NOTES': '\n'.join(package.get('teacher_prompt', []))
            })

    if worksheet_blocks:
        lesson_title = plan.get('meta', {}).get('title', '학습지')
        chunks = []
        n = len(worksheet_blocks)
        idx = 0
        while n > 0:
            if n == 4:
                chunks.append(worksheet_blocks[idx:idx+2])
                chunks.append(worksheet_blocks[idx+2:idx+4])
                break
            elif n == 5:
                chunks.append(worksheet_blocks[idx:idx+3])
                chunks.append(worksheet_blocks[idx+3:idx+5])
                break
            else:
                take = min(3, n)
                chunks.append(worksheet_blocks[idx:idx+take])
                idx += take
                n -= take
                
        total_pages = len(chunks)
        q_idx = 1
        for i, chunk in enumerate(chunks):
            page_title = lesson_title
            if total_pages > 1:
                page_title = f"{lesson_title} ({i+1}/{total_pages})"
            
            pages.append({'page_type': 'worksheet', 'title': page_title, 'blocks': chunk, 'start_q_idx': q_idx})
            pages.append({'page_type': 'answer_key', 'title': f"{page_title} 정답지", 'blocks': chunk, 'start_q_idx': q_idx})
            q_idx += len(chunk)
            
    return pages


def render_page(page: dict, page_index: int) -> str:
    page_type = page.get('page_type', 'slide')
    if page_type in {'worksheet', 'answer_key'}:
        return render_worksheet_page(page, page_index, page_type)
    return tag_page_section(render_slide(page), 'slide', page_index)


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

    pages_data = normalize_pages(plan)
    slides_data = [page for page in pages_data if page.get('page_type', 'slide') == 'slide']

    # 페이지 렌더링
    rendered_pages = []
    current_section_header = ""
    for idx, slide in enumerate(pages_data):
        slide['SLIDE_INDEX'] = idx
        if 'SECTION_HEADER' in slide:
            current_section_header = slide['SECTION_HEADER']
        elif current_section_header and slide.get('page_type', 'slide') == 'slide':
            slide['SECTION_HEADER'] = current_section_header

        rendered_pages.append(render_page(slide, idx))

    slides_content = "\n".join(rendered_pages)

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
    print(f"   슬라이드 수: {len(slides_data)}장 / 전체 페이지 수: {len(pages_data)}장")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("사용법: python build_html.py <입력_json> <출력_html>")
        sys.exit(1)

    build_html(sys.argv[1], sys.argv[2])
