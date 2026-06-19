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

    # 이미지 프레임 스타일 동적 파생
    frame_preset = theme_colors.get('image_frame_preset', 'business')
    frame_dot_border = "none"
    frame_css = ""
    
    if frame_preset == 'cute':
        frame_bg = "#fffbf0"
        frame_border = f"2px dashed {accent}"
        frame_shadow = "6px 6px 0px rgba(0, 0, 0, 0.04)"
        frame_radius = "20px"
        frame_dots = "flex"
        frame_header_bg = "transparent"
        frame_css = f"""
.screenshot-frame {{
    padding-top: 10px !important;
}}
.browser-frame .frame-dots {{
    display: block !important;
    height: 12px;
    background: transparent !important;
    border: none !important;
    position: relative;
}}
.browser-frame .frame-dots::before {{
    content: '';
    position: absolute;
    top: -8px;
    left: 50%;
    transform: translateX(-50%) rotate(-2deg);
    width: 70px;
    height: 18px;
    background: rgba(251, 191, 36, 0.7); /* 마스킹 테이프 */
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border-left: 2px dashed rgba(0,0,0,0.15);
    border-right: 2px dashed rgba(0,0,0,0.15);
}}
.browser-frame .dot {{
    display: none !important;
}}
"""
    elif frame_preset == 'tech':
        frame_bg = "rgba(15, 23, 42, 0.65)"
        frame_border = f"1px solid {accent}"
        frame_shadow = f"0 0 15px {accent}4D"
        frame_radius = "0px"
        frame_dots = "none"
        frame_header_bg = "rgba(0, 0, 0, 0.2)"
        frame_css = f"""
.browser-frame .frame-dots {{
    display: flex !important;
    align-items: center;
    background: rgba(0, 0, 0, 0.4) !important;
    border-bottom: 1px solid {accent} !important;
    height: 24px;
    padding: 0 10px;
}}
.browser-frame .frame-dots::before {{
    content: 'SYS.terminal@root:~';
    font-family: 'Orbitron', monospace;
    font-size: 10px;
    color: {accent_secondary};
    opacity: 0.8;
    letter-spacing: 1px;
}}
.browser-frame .dot {{
    display: none !important;
}}
"""
    elif frame_preset == 'retro':
        frame_bg = "#ffffff"
        frame_border = f"3px solid {text}"
        frame_shadow = f"8px 8px 0px {text}"
        frame_radius = "4px"
        frame_dots = "none"
        frame_header_bg = "transparent"
        frame_css = f"""
.screenshot-frame {{
    padding: 10px 10px 32px 10px !important;
}}
.browser-frame .frame-dots {{
    display: none !important;
}}
"""
    elif frame_preset == 'minimal':
        frame_bg = "transparent"
        frame_border = "none"
        frame_shadow = "0 15px 35px rgba(0,0,0,0.12)"
        frame_radius = "6px"
        frame_dots = "none"
        frame_header_bg = "transparent"
        frame_css = f"""
.screenshot-frame {{
    padding: 0 !important;
}}
.browser-frame .frame-dots {{
    display: none !important;
}}
"""
    else: # business / auto / fallback
        frame_bg = bg_secondary
        frame_border = "1px solid rgba(0, 0, 0, 0.08)" if is_light else "1px solid rgba(255, 255, 255, 0.1)"
        frame_shadow = "0 8px 24px rgba(0, 0, 0, 0.06)" if is_light else "0 10px 30px rgba(0, 0, 0, 0.2)"
        frame_radius = "12px"
        frame_dots = "flex"
        frame_header_bg = "rgba(0, 0, 0, 0.04)" if is_light else "rgba(255, 255, 255, 0.04)"
        frame_css = f"""
.browser-frame .frame-dots {{
    display: var(--image-frame-dots-display) !important;
    background: var(--image-frame-header-bg) !important;
}}
.browser-frame .dot {{
    display: block !important;
}}
"""

    # 1. 카드 프리셋 CSS 생성
    card_preset = theme_colors.get('card_style_preset', 'business_clean')
    card_css = ""
    if card_preset == 'cute_note':
        card_css = """
.reveal .card, .reveal .stat-card-button, .reveal .roadmap-step, .reveal .ox-column, .reveal .matrix-cell {
    --color-card-bg: #fffbf0;
    --color-card-border: 2px dashed rgba(0, 0, 0, 0.12);
    --color-text: #2c2c2c;
    --color-text-secondary: #555555;
    color: #2c2c2c !important;
    border: 2px dashed rgba(0, 0, 0, 0.12) !important;
    border-radius: 20px !important;
    box-shadow: 5px 5px 0px rgba(0, 0, 0, 0.05) !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}
"""
    elif card_preset == 'tech_neon':
        card_css = f"""
.reveal .card, .reveal .stat-card-button, .reveal .roadmap-step, .reveal .ox-column, .reveal .matrix-cell {{
    --color-card-bg: rgba(15, 23, 42, 0.65);
    --color-card-border: 1px solid {accent};
    border: 1px solid {accent} !important;
    border-radius: 4px !important;
    box-shadow: 0 0 15px rgba(99, 102, 241, 0.25) !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}}
"""
    elif card_preset == 'business_clean':
        card_css = """
.reveal .card, .reveal .stat-card-button, .reveal .roadmap-step, .reveal .ox-column, .reveal .matrix-cell {
    --color-card-bg: var(--color-bg-secondary);
    --color-card-border: 1px solid rgba(0, 0, 0, 0.06);
    border: 1px solid rgba(0, 0, 0, 0.06) !important;
    border-radius: 10px !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.04) !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}
"""
    elif card_preset == 'editorial_serif':
        card_css = f"""
.reveal .card, .reveal .stat-card-button, .reveal .roadmap-step, .reveal .ox-column, .reveal .matrix-cell {{
    --color-card-bg: transparent;
    --color-card-border: none;
    border-top: 2px solid {text} !important;
    border-bottom: 2px solid {text} !important;
    border-left: none !important;
    border-right: none !important;
    border-radius: 0px !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}}
"""
    elif card_preset == 'retro_bold':
        card_css = f"""
.reveal .card, .reveal .stat-card-button, .reveal .roadmap-step, .reveal .ox-column, .reveal .matrix-cell {{
    --color-card-bg: #ffffff;
    --color-card-border: 3px solid {text};
    --color-text: #1e293b;
    --color-text-secondary: #475569;
    color: #1e293b !important;
    border: 3px solid {text} !important;
    border-radius: 12px !important;
    box-shadow: 6px 6px 0px {text} !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}}
"""
    elif card_preset == 'transparent':
        card_css = """
.reveal .card, .reveal .stat-card-button, .reveal .roadmap-step, .reveal .ox-column, .reveal .matrix-cell {
    --color-card-bg: transparent;
    --color-card-border: none;
    border: none !important;
    border-radius: 0px !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}
"""

    # 2. 아이콘 프리셋 CSS 생성
    icon_preset = theme_colors.get('icon_preset', 'business')
    icon_css = ""
    if icon_preset == 'cute':
        icon_css = f"""
.reveal .bullet-list li::before, .reveal .bullet-icon {{
    border-radius: 50% !important;
    border: 2px solid {accent} !important;
    color: {accent_secondary} !important;
    background-color: var(--color-bg-secondary) !important;
    display: inline-flex; justify-content: center; align-items: center; width: 1.5em; height: 1.5em;
}}
"""
    elif icon_preset == 'tech':
        icon_css = f"""
.reveal .bullet-icon {{
    background-color: rgba(99, 102, 241, 0.1) !important;
    border-radius: 4px !important;
    border: 1px solid {accent} !important;
    color: {accent} !important;
    box-shadow: 0 0 10px rgba(99, 102, 241, 0.4) !important;
    display: inline-flex; justify-content: center; align-items: center; width: 1.5em; height: 1.5em;
}}
"""
    elif icon_preset == 'business':
        icon_css = """
.reveal .bullet-icon {
    background-color: var(--color-bg-secondary) !important;
    border-radius: 8px !important;
    border: 1px solid rgba(0, 0, 0, 0.08) !important;
    color: var(--color-text-secondary) !important;
    display: inline-flex; justify-content: center; align-items: center; width: 1.5em; height: 1.5em;
}
"""
    elif icon_preset == 'minimal_raw':
        icon_css = f"""
.reveal .bullet-icon {{
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    color: {accent} !important;
    display: inline-flex; justify-content: center; align-items: center; width: 1.5em; height: 1.5em;
}}
"""
    elif icon_preset == 'handdrawn':
        icon_css = """
.reveal .bullet-icon {
    background-color: #fef08a !important;
    border: 2px solid #000 !important;
    border-radius: 40% 60% 70% 30% / 40% 50% 60% 50% !important;
    color: #000 !important;
    transform: rotate(-3deg);
    display: inline-flex; justify-content: center; align-items: center; width: 1.5em; height: 1.5em;
}
"""

    # 3. 폰트 프리셋 매칭
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

    # 4. 강조 텍스트(strong) 스타일 CSS 생성
    highlight_preset = theme_colors.get('highlight_style', theme_colors.get('strong_style', 'friendly'))
    highlight_css = ""
    if highlight_preset == 'friendly':
        highlight_css = f"""
.reveal strong {{
    position: relative; display: inline-block; font-weight: 800; color: inherit; z-index: 1;
}}
.reveal strong::after {{
    content: ""; position: absolute; left: 0; bottom: 2px; width: 100%; height: 35%;
    background-color: {accent_secondary}; opacity: 0.55; z-index: -1; border-radius: 4px;
}}
"""
    elif highlight_preset == 'cyber':
        highlight_css = f"""
.reveal strong {{
    font-weight: 900; color: {accent_secondary}; text-shadow: 0 0 8px rgba(165, 180, 252, 0.4); font-family: 'Orbitron', sans-serif;
}}
.reveal strong::before {{
    content: "["; color: {accent}; margin-right: 2px;
}}
.reveal strong::after {{
    content: "]"; color: {accent}; margin-left: 2px;
}}
"""
    elif highlight_preset == 'classic':
        highlight_css = f"""
.reveal strong {{
    font-style: italic; font-weight: 700; color: {accent}; border-bottom: 3px double {accent}; padding-bottom: 1px;
}}
"""
    elif highlight_preset == 'editorial':
        highlight_css = f"""
.reveal strong {{
    font-weight: 800; background: {text}; color: {bg}; padding: 0px 4px; border-radius: 2px;
}}
"""
    elif highlight_preset == 'chalkboard':
        highlight_css = """
.reveal strong {
    font-weight: 900; color: #b91c1c; text-decoration: underline wavy #b91c1c; text-underline-offset: 4px;
}
"""

    # 5. 하단 요약바 스타일 CSS 생성
    takeaway_preset = theme_colors.get('takeaway_style', 'friendly')
    takeaway_css = ""
    if takeaway_preset == 'friendly':
        takeaway_css = f"""
.reveal .bottom-takeaway-bar {{
    background: linear-gradient(90deg, {accent}, {accent_secondary}) !important;
    border-radius: 20px 20px 0 0 !important;
    margin: 0 15px !important;
    width: calc(100% - 30px) !important;
    bottom: 5px !important;
    box-shadow: 0 -5px 20px rgba(0,0,0,0.06) !important;
}}
"""
    elif takeaway_preset == 'cyber':
        takeaway_css = f"""
.reveal .bottom-takeaway-bar {{
    background: rgba(15, 23, 42, 0.9) !important;
    border-top: 2px solid {accent} !important;
    clip-path: polygon(0 0, 93% 0, 100% 100%, 0% 100%) !important;
    color: {accent_secondary} !important;
    text-shadow: 0 0 5px rgba(165, 180, 252, 0.4) !important;
}}
"""
    elif takeaway_preset == 'classic':
        takeaway_css = f"""
.reveal .bottom-takeaway-bar {{
    background: var(--color-bg-secondary) !important;
    border-top: 1px solid {accent} !important;
    color: {text} !important;
    font-family: 'Playfair Display', serif !important;
    font-style: italic !important;
}}
"""
    elif takeaway_preset == 'editorial':
        takeaway_css = f"""
.reveal .bottom-takeaway-bar {{
    background: transparent !important;
    border-top: 2px solid {text} !important;
    color: {text} !important;
    padding: 15px 0px !important;
    margin: 0 40px !important;
    width: calc(100% - 80px) !important;
    box-shadow: none !important;
}}
"""
    elif takeaway_preset == 'chalkboard':
        takeaway_css = """
.reveal .bottom-takeaway-bar {
    background: #8b4513 !important;
    border-top: 4px solid #5c2c0c !important;
    border-radius: 10px 10px 0 0 !important;
    color: #ffedd5 !important;
    font-family: 'Nanum Pen Script', cursive !important;
    font-size: 1.3rem !important;
}
"""

    # 6. 화면 전환 모션 transition 생성
    motion_preset = theme_colors.get('motion_preset', 'friendly')
    motion_css = ""
    if motion_preset == 'friendly':
        motion_css = ".reveal { --slide-transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275); }"
    elif motion_preset == 'cyber':
        motion_css = ".reveal { --slide-transition: all 0.22s cubic-bezier(0.19, 1, 0.22, 1); }"
    elif motion_preset == 'classic':
        motion_css = ".reveal { --slide-transition: all 0.75s cubic-bezier(0.25, 1, 0.5, 1); }"
    elif motion_preset == 'editorial':
        motion_css = ".reveal { --slide-transition: all 0.45s cubic-bezier(0.77, 0, 0.175, 1); }"
    elif motion_preset == 'chalkboard':
        motion_css = ".reveal { --slide-transition: all 0.45s cubic-bezier(0.4, 0, 0.2, 1); }"

    # 7. 배경 패턴 CSS 생성
    pattern_preset = theme_colors.get('bg_pattern_style', 'none')
    pattern_css = ""
    if pattern_preset == 'grid':
        pattern_css = f"""
.pattern-overlay {{
    opacity: 0.12 !important;
    background-size: 30px 30px;
    background-image: 
        linear-gradient(to right, {text_secondary} 1px, transparent 1px),
        linear-gradient(to bottom, {text_secondary} 1px, transparent 1px) !important;
}}
"""
    elif pattern_preset == 'dots':
        pattern_css = f"""
.pattern-overlay {{
    opacity: 0.12 !important;
    background-size: 20px 20px;
    background-image: radial-gradient({text_secondary} 1.5px, transparent 1.5px) !important;
}}
"""
    elif pattern_preset == 'diagonal':
        pattern_css = f"""
.pattern-overlay {{
    opacity: 0.12 !important;
    background-size: 40px 40px;
    background-image: linear-gradient(45deg, 
        {text_secondary} 1px, transparent 1px, 
        transparent 19px, {text_secondary} 20px, 
        transparent 20px, transparent 39px, {text_secondary} 40px
    ) !important;
}}
"""
    elif pattern_preset == 'blueprint':
        pattern_css = f"""
.pattern-overlay {{
    opacity: 0.25 !important;
    background-size: 40px 40px;
    background-image: 
        linear-gradient(to right, {accent} 1.5px, transparent 1.5px),
        linear-gradient(to bottom, {accent} 1.5px, transparent 1.5px) !important;
}}
"""
    elif pattern_preset == 'terrazzo':
        pattern_css = f"""
.pattern-overlay {{
    opacity: 0.12 !important;
    background-size: 120px 120px;
    background-image: 
        radial-gradient(circle at 20% 30%, {accent} 4px, transparent 8px),
        radial-gradient(circle at 75% 15%, {accent_secondary} 6px, transparent 12px),
        radial-gradient(circle at 50% 80%, {text_secondary} 5px, transparent 10px) !important;
}}
"""

    # 8. 배경 장식 활성화 CSS 생성
    decorations = theme_colors.get('decorations', [])
    decor_css_list = []
    if decorations:
        checkbox_mappings = {
            'corner_accent': ['.decor-corner-tl', '.decor-corner-tr', '.decor-corner-bl', '.decor-corner-br'],
            'circles': ['.decor-circle-1', '.decor-circle-2'],
            'hud_brackets': ['.decor-hud-left', '.decor-hud-right'],
            'wavy_line': ['.decor-wavy'],
            'geometric_shapes': ['.decor-shape-1', '.decor-shape-2', '.decor-shape-3', '.decor-shape-4'],
            'tech_grid_lines': ['.decor-techlines']
        }
        for decor in decorations:
            if decor in checkbox_mappings:
                selectors = ", ".join(checkbox_mappings[decor])
                opacity_val = "0.25" if decor == 'wavy_line' else ("0.35" if decor == 'tech_grid_lines' else ("0.18" if decor == 'circles' else ("0.22" if decor == 'geometric_shapes' else "0.3")))
                decor_css_list.append(f"""
{selectors} {{
    opacity: {opacity_val} !important;
}}
""")
    decor_css = "\n".join(decor_css_list)

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
    
    /* 이미지 프레임 (테마 제어 요소) */
    --image-frame-bg: {frame_bg};
    --image-frame-border: {frame_border};
    --image-frame-shadow: {frame_shadow};
    --image-frame-radius: {frame_radius};
    --image-frame-dots-display: {frame_dots};
    --image-frame-header-bg: {frame_header_bg};
    --image-frame-dot-border: {frame_dot_border};
}}

/* 프리셋 연동 CSS 구동 */
{frame_css}
{card_css}
{icon_css}
{highlight_css}
{takeaway_css}
{motion_css}
{pattern_css}
{decor_css}

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
