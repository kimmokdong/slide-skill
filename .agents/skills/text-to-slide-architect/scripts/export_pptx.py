#!/usr/bin/env python3
"""JSON 설계도(slide_plan.json)를 읽어 편집 가능한 네이티브 PPTX로 내보내는 스크립트.

사용법:
    python export_pptx.py <입력_json> <출력.pptx> [html디렉토리(이미지상대경로용)]

의존성:
    pip install python-pptx
"""

import sys
import os
import json

def export_pptx(input_json: str, output_path: str, html_dir: str = None) -> None:
    """JSON 설계도를 읽어 PPTX 객체(텍스트박스/도형)로 정교하게 변환합니다."""
    try:
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
    except ImportError:
        print("오류: python-pptx가 설치되지 않았습니다.")
        print("설치 명령: pip install python-pptx")
        sys.exit(1)

    if not os.path.exists(input_json):
        print(f"오류: 파일을 찾을 수 없습니다: {input_json}")
        sys.exit(1)

    with open(input_json, "r", encoding="utf-8") as f:
        plan = json.load(f)

    meta = plan.get('meta', {})
    slides_data = plan.get('slides', [])
    theme_name = meta.get('theme', 'tech_blue')
    
    if not html_dir:
        html_dir = os.path.dirname(os.path.abspath(input_json))

    # PPTX 생성 (16:9 와이드스크린)
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 기본 테마 팔레트 (RGB)
    themes = {
        'tech_blue': {'bg': (15, 23, 42), 'ink': (241, 245, 249), 'accent': (59, 130, 246), 'muted': (148, 163, 184)},
        'warm_edu': {'bg': (255, 251, 245), 'ink': (28, 25, 23), 'accent': (245, 158, 11), 'muted': (87, 83, 78)},
        'soft_pink': {'bg': (253, 242, 248), 'ink': (28, 25, 23), 'accent': (236, 72, 153), 'muted': (107, 114, 128)},
        'mono_dark': {'bg': (17, 24, 39), 'ink': (249, 250, 251), 'accent': (107, 114, 128), 'muted': (156, 163, 175)},
    }
    
    c = themes.get(theme_name, themes['tech_blue']).copy()

    def hex_to_rgb_tuple(value, fallback):
        if not isinstance(value, str):
            return fallback
        value = value.strip().lstrip('#')
        if len(value) == 3:
            value = ''.join(ch * 2 for ch in value)
        if len(value) != 6:
            return fallback
        try:
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            return fallback

    theme_colors = meta.get('theme_colors') or {}
    if theme_colors:
        c['bg'] = hex_to_rgb_tuple(theme_colors.get('bg'), c['bg'])
        c['ink'] = hex_to_rgb_tuple(theme_colors.get('text'), c['ink'])
        c['accent'] = hex_to_rgb_tuple(theme_colors.get('accent'), c['accent'])
        c['muted'] = hex_to_rgb_tuple(theme_colors.get('text_secondary'), c['muted'])
    
    def rgb(tup):
        return RGBColor(tup[0], tup[1], tup[2])

    def item_text(item, title_key='title', label_key='label', desc_key='desc'):
        if isinstance(item, dict):
            title = item.get(title_key) or item.get(label_key) or item.get('text') or ''
            desc = item.get(desc_key) or ''
            return f"{title}: {desc}" if title and desc else str(title or desc)
        return str(item)

    def normalize_slide_data(data):
        normalized = data.copy()
        stype = normalized.get('layout', normalized.get('type', 'title'))
        normalized['type'] = stype

        if stype == 'text_image' and not normalized.get('CONTENT') and normalized.get('BODY'):
            normalized['CONTENT'] = normalized.get('BODY', '')
        if stype == 'quiz':
            if not normalized.get('QUESTION') and normalized.get('QUIZ_QUESTION'):
                normalized['QUESTION'] = normalized.get('QUIZ_QUESTION', '')
            if not normalized.get('QUIZ_OPTIONS') and normalized.get('OPTIONS'):
                normalized['QUIZ_OPTIONS'] = normalized.get('OPTIONS', [])
            if normalized.get('ANSWER') and 'ANSWER_INDEX' not in normalized and normalized.get('QUIZ_OPTIONS'):
                for opt_idx, option in enumerate(normalized.get('QUIZ_OPTIONS', [])):
                    option_text = option.get('text', option) if isinstance(option, dict) else option
                    if str(option_text).strip() == str(normalized.get('ANSWER')).strip():
                        normalized['ANSWER_INDEX'] = opt_idx
                        break
        if stype == 'closing' and not normalized.get('MESSAGE') and normalized.get('SUBTITLE'):
            normalized['MESSAGE'] = normalized.get('SUBTITLE', '')
        return normalized

    blank_layout = prs.slide_layouts[6]

    current_section_header = ""
    for idx, data in enumerate(slides_data):
        data = normalize_slide_data(data)
        if 'SECTION_HEADER' in data:
            current_section_header = data['SECTION_HEADER']
        elif current_section_header:
            data['SECTION_HEADER'] = current_section_header

        slide = prs.slides.add_slide(blank_layout)
        
        # 배경색 설정
        background = slide.background
        fill = background.fill
        fill.solid()
        
        stype = data.get('type', 'title')
        
        # Hero / Closing 은 좀 더 다크하게 (테크블루는 이미 다크지만)
        if stype in ['hero', 'closing']:
            fill.fore_color.rgb = rgb(c['bg']) # 임시로 같게 처리, 고도화 가능
        else:
            fill.fore_color.rgb = rgb(c['bg'])

        # 제목 렌더링 헬퍼
        def add_title(text, is_hero=False, is_closing=False):
            if not text: return
            y = 2.5 if is_hero or is_closing else 0.5
            h = 1.5 if is_hero or is_closing else 1.0
            size = 54 if is_hero or is_closing else 44
            align = PP_ALIGN.CENTER if is_hero or is_closing else PP_ALIGN.LEFT
            
            box = slide.shapes.add_textbox(Inches(0.9), Inches(y), Inches(11.5), Inches(h))
            tf = box.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.text = text
            p.font.size = Pt(size)
            p.font.bold = True
            p.font.color.rgb = rgb(c['ink']) if not (is_hero or is_closing) else rgb(c['accent'])
            p.alignment = align

        # 발표자 노트
        if data.get('SPEAKER_NOTES'):
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = data.get('SPEAKER_NOTES')

        # 섹션 헤더 (좌측 상단 네비게이션)
        if data.get('SECTION_HEADER') and stype != 'fullbleed':
            sh_box = slide.shapes.add_textbox(Inches(0.9), Inches(0.2), Inches(5.0), Inches(0.4))
            shp = sh_box.text_frame.paragraphs[0]
            shp.text = data['SECTION_HEADER']
            shp.font.size = Pt(14)
            shp.font.bold = True
            shp.font.color.rgb = rgb(c['accent'])

        # 슬라이드 타입별 레이아웃 분기
        if stype == 'hero':
            if data.get('BADGE'):
                b = slide.shapes.add_textbox(Inches(0.9), Inches(1.8), Inches(11.5), Inches(0.5))
                b.text_frame.paragraphs[0].text = data['BADGE']
                b.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                b.text_frame.paragraphs[0].font.color.rgb = rgb(c['accent'])
            
            add_title(data.get('TITLE'), is_hero=True)
            
            if data.get('SUBTITLE'):
                sub = slide.shapes.add_textbox(Inches(0.9), Inches(4.0), Inches(11.5), Inches(1.0))
                p = sub.text_frame.paragraphs[0]
                p.text = data['SUBTITLE']
                p.alignment = PP_ALIGN.CENTER
                p.font.size = Pt(28)
                p.font.color.rgb = rgb(c['muted'])

        elif stype == 'closing':
            add_title(data.get('TITLE'), is_closing=True)
            if data.get('MESSAGE'):
                sub = slide.shapes.add_textbox(Inches(0.9), Inches(4.0), Inches(11.5), Inches(1.0))
                p = sub.text_frame.paragraphs[0]
                p.text = data['MESSAGE']
                p.alignment = PP_ALIGN.CENTER
                p.font.size = Pt(28)
                p.font.color.rgb = rgb(c['muted'])

        elif stype == 'title':
            add_title(data.get('TITLE'), is_hero=True)
            if data.get('SUBTITLE'):
                sub = slide.shapes.add_textbox(Inches(0.9), Inches(4.0), Inches(11.5), Inches(1.0))
                p = sub.text_frame.paragraphs[0]
                p.text = data['SUBTITLE']
                p.alignment = PP_ALIGN.CENTER
                p.font.size = Pt(28)
                p.font.color.rgb = rgb(c['muted'])

        elif stype == 'bullet' or stype == 'summary':
            add_title(data.get('TITLE'))
            items = data.get('BULLET_ITEMS') or data.get('SUMMARY_ITEMS') or []
            if items:
                box = slide.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(11.5), Inches(5.0))
                tf = box.text_frame
                tf.word_wrap = True
                for i, item in enumerate(items):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    prefix = f"{i+1}. " if stype == 'summary' else "• "
                    p.text = prefix + item_text(item)
                    p.font.size = Pt(24)
                    p.font.color.rgb = rgb(c['ink'])
                    p.space_after = Pt(14)

        elif stype == 'text_image':
            add_title(data.get('TITLE'))
            # Text left
            if data.get('CONTENT'):
                box = slide.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(5.5), Inches(5.0))
                p = box.text_frame.paragraphs[0]
                p.text = data['CONTENT']
                p.font.size = Pt(24)
                p.font.color.rgb = rgb(c['ink'])
            # Image right
            img_src = data.get('IMAGE_SRC')
            if img_src:
                img_path = os.path.join(html_dir, img_src)
                if os.path.exists(img_path):
                    try:
                        slide.shapes.add_picture(img_path, Inches(7.0), Inches(2.0), width=Inches(5.5))
                    except Exception:
                        pass

        elif stype == 'comparison':
            add_title(data.get('TITLE'))
            # Left
            boxL = slide.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(5.5), Inches(5.0))
            pL = boxL.text_frame.paragraphs[0]
            pL.text = data.get('LEFT_TITLE', 'Left')
            pL.font.bold = True
            pL.font.size = Pt(28)
            for item in data.get('LEFT_ITEMS', []):
                p = boxL.text_frame.add_paragraph()
                p.text = "• " + str(item)
                p.font.size = Pt(20)
            # Right
            boxR = slide.shapes.add_textbox(Inches(6.9), Inches(2.0), Inches(5.5), Inches(5.0))
            pR = boxR.text_frame.paragraphs[0]
            pR.text = data.get('RIGHT_TITLE', 'Right')
            pR.font.bold = True
            pR.font.size = Pt(28)
            pR.font.color.rgb = rgb(c['accent'])
            for item in data.get('RIGHT_ITEMS', []):
                p = boxR.text_frame.add_paragraph()
                p.text = "• " + str(item)
                p.font.size = Pt(20)

        elif stype == 'vs_ox':
            add_title(data.get('TITLE'))
            groups = [
                (data.get('O_TITLE', 'O'), data.get('O_ITEMS', []), 0.9),
                (data.get('X_TITLE', 'X'), data.get('X_ITEMS', []), 6.9),
            ]
            for title, items, x in groups:
                box = slide.shapes.add_textbox(Inches(x), Inches(2.0), Inches(5.5), Inches(5.0))
                tf = box.text_frame
                tf.word_wrap = True
                head = tf.paragraphs[0]
                head.text = title
                head.font.bold = True
                head.font.size = Pt(28)
                head.font.color.rgb = rgb(c['accent'])
                for item in items:
                    p = tf.add_paragraph()
                    text = item.get('text', item_text(item)) if isinstance(item, dict) else str(item)
                    marker = item.get('marker', '') if isinstance(item, dict) else ''
                    p.text = f"{marker} {text}".strip()
                    p.font.size = Pt(20)
                    p.font.color.rgb = rgb(c['ink'])

        elif stype == 'matrix':
            add_title(data.get('TITLE'))
            if data.get('SUBTITLE'):
                sub = slide.shapes.add_textbox(Inches(0.9), Inches(1.35), Inches(11.5), Inches(0.5))
                sp = sub.text_frame.paragraphs[0]
                sp.text = data.get('SUBTITLE')
                sp.font.size = Pt(18)
                sp.font.color.rgb = rgb(c['muted'])
            items = data.get('MATRIX_ITEMS', [])
            positions = [(0.9, 2.0), (6.9, 2.0), (0.9, 4.55), (6.9, 4.55)]
            for i, item in enumerate(items[:4]):
                x, y = positions[i]
                box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(5.5), Inches(2.1))
                tf = box.text_frame
                tf.word_wrap = True
                label = tf.paragraphs[0]
                label.text = item.get('label', item.get('title', str(item))) if isinstance(item, dict) else str(item)
                label.font.bold = True
                label.font.size = Pt(24)
                label.font.color.rgb = rgb(c['accent'])
                if isinstance(item, dict) and item.get('desc'):
                    desc = tf.add_paragraph()
                    desc.text = item.get('desc', '')
                    desc.font.size = Pt(17)
                    desc.font.color.rgb = rgb(c['ink'])

        elif stype == 'timeline':
            add_title(data.get('TITLE'))
            items = data.get('TIMELINE_ITEMS', [])
            if items:
                box = slide.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(11.5), Inches(5.0))
                for i, item in enumerate(items):
                    if isinstance(item, dict):
                        when = item.get('date', '')
                        title = item.get('title', '')
                        desc = item.get('desc', '')
                        p = box.text_frame.paragraphs[0] if i == 0 else box.text_frame.add_paragraph()
                        label = f"[{when}] " if when else ""
                        p.text = f"{label}{title}: {desc}" if title and desc else f"{label}{title or desc}"
                        p.font.size = Pt(24)
                        p.space_after = Pt(14)
                        p.font.color.rgb = rgb(c['ink'])
                    else:
                        p = box.text_frame.paragraphs[0] if i == 0 else box.text_frame.add_paragraph()
                        p.text = str(item)
                        p.font.size = Pt(24)
                        p.space_after = Pt(14)
                        p.font.color.rgb = rgb(c['ink'])

        elif stype == 'roadmap':
            add_title(data.get('TITLE'))
            items = data.get('ROADMAP_ITEMS', [])
            if items:
                width = 11.5 / max(len(items), 1)
                for i, item in enumerate(items):
                    x = 0.9 + (i * width)
                    box = slide.shapes.add_textbox(Inches(x), Inches(2.2), Inches(width - 0.15), Inches(4.2))
                    tf = box.text_frame
                    tf.word_wrap = True
                    num = tf.paragraphs[0]
                    num.text = f"{i+1}"
                    num.font.size = Pt(28)
                    num.font.bold = True
                    num.font.color.rgb = rgb(c['accent'])

                    label = tf.add_paragraph()
                    label.text = item.get('label', item.get('title', str(item))) if isinstance(item, dict) else str(item)
                    label.font.size = Pt(22)
                    label.font.bold = True
                    label.font.color.rgb = rgb(c['ink'])

                    if isinstance(item, dict) and item.get('desc'):
                        desc = tf.add_paragraph()
                        desc.text = item.get('desc', '')
                        desc.font.size = Pt(16)
                        desc.font.color.rgb = rgb(c['muted'])

        elif stype == 'stats':
            add_title(data.get('TITLE'))
            items = data.get('STAT_ITEMS', [])
            width = 11.5 / max(len(items), 1)
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    x = 0.9 + (i * width)
                    box = slide.shapes.add_textbox(Inches(x), Inches(3.0), Inches(width), Inches(2.0))
                    val_p = box.text_frame.paragraphs[0]
                    val_p.text = str(item.get('value', ''))
                    val_p.font.size = Pt(54)
                    val_p.font.bold = True
                    val_p.font.color.rgb = rgb(c['accent'])
                    val_p.alignment = PP_ALIGN.CENTER
                    
                    lbl_p = box.text_frame.add_paragraph()
                    lbl_p.text = str(item.get('label', ''))
                    lbl_p.font.size = Pt(24)
                    lbl_p.font.color.rgb = rgb(c['muted'])
                    lbl_p.alignment = PP_ALIGN.CENTER

        elif stype == 'diagram':
            add_title(data.get('TITLE'))
            img_src = data.get('DIAGRAM_SRC')
            if img_src:
                img_path = os.path.join(html_dir, img_src)
                if os.path.exists(img_path):
                    try:
                        slide.shapes.add_picture(img_path, Inches(3.0), Inches(2.0), width=Inches(7.3))
                    except Exception:
                        pass
            if data.get('DIAGRAM_CAPTION'):
                cap = slide.shapes.add_textbox(Inches(0.9), Inches(6.8), Inches(11.5), Inches(0.5))
                cap.text_frame.paragraphs[0].text = data['DIAGRAM_CAPTION']
                cap.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                cap.text_frame.paragraphs[0].font.size = Pt(20)

        elif stype == 'quiz':
            add_title(data.get('QUESTION', 'Quiz'), is_hero=True)
            opts = data.get('QUIZ_OPTIONS', [])
            if opts:
                box = slide.shapes.add_textbox(Inches(0.9), Inches(3.5), Inches(11.5), Inches(3.5))
                for i, opt in enumerate(opts):
                    text = opt.get('text', '') if isinstance(opt, dict) else str(opt)
                    p = box.text_frame.paragraphs[0] if i == 0 else box.text_frame.add_paragraph()
                    p.text = f"{chr(65+i)}. {text}"
                    if data.get('ANSWER_INDEX') == i:
                        p.text += " *"
                    p.font.size = Pt(24)
                    p.font.color.rgb = rgb(c['ink'])
                    p.space_after = Pt(14)

        elif stype == 'quote':
            box = slide.shapes.add_textbox(Inches(0.9), Inches(3.0), Inches(11.5), Inches(3.0))
            p = box.text_frame.paragraphs[0]
            p.text = f'"{data.get("QUOTE_TEXT", "")}"'
            p.font.size = Pt(40)
            p.font.italic = True
            p.font.color.rgb = rgb(c['ink'])
            p.alignment = PP_ALIGN.CENTER
            
            if data.get('QUOTE_SOURCE'):
                src = slide.shapes.add_textbox(Inches(0.9), Inches(5.0), Inches(11.5), Inches(1.0))
                p2 = src.text_frame.paragraphs[0]
                p2.text = f"— {data['QUOTE_SOURCE']}"
                p2.font.size = Pt(24)
                p2.font.color.rgb = rgb(c['muted'])
                p2.alignment = PP_ALIGN.CENTER

        elif stype == 'tutorial':
            # 스텝퍼 바 (상단)
            stepper_items = data.get('STEPPER_ITEMS', [])
            if stepper_items:
                stepper_text_parts = []
                for i, step_info in enumerate(stepper_items):
                    if isinstance(step_info, dict):
                        label = step_info.get('label', f'Step {i+1}')
                        state = step_info.get('state', 'inactive')
                    else:
                        label = str(step_info)
                        state = 'inactive'
                    marker = '●' if state == 'active' else ('✓' if state == 'completed' else '○')
                    stepper_text_parts.append(f"{marker} {label}")
                stepper_box = slide.shapes.add_textbox(Inches(0.9), Inches(0.9), Inches(11.5), Inches(0.5))
                sp = stepper_box.text_frame.paragraphs[0]
                sp.text = "  ─  ".join(stepper_text_parts)
                sp.font.size = Pt(20) # 스텝퍼를 제목 크기로 격상
                sp.font.color.rgb = rgb(c['muted'])
                sp.font.bold = True
                sp.alignment = PP_ALIGN.LEFT # 좌측 정렬로 통일

            # 제목 (스텝퍼 아래의 부제목 역할)
            step_num = data.get('STEP_NUMBER', '')
            title_text = data.get('TITLE', '')
            if step_num:
                title_text = f"[Step {step_num}] {title_text}"
            box_title = slide.shapes.add_textbox(Inches(0.9), Inches(1.5), Inches(5.5), Inches(0.4))
            box_title.text_frame.word_wrap = False
            tp = box_title.text_frame.paragraphs[0]
            tp.text = title_text
            tp.font.size = Pt(24) # 작게 표시
            tp.font.color.rgb = rgb(c['ink'])

            # 좌측: 불릿 항목 (원래 위치인 2.0으로 복귀)
            items = data.get('BULLET_ITEMS', [])
            if items:
                box_items = slide.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(5.5), Inches(3.5))
                tf = box_items.text_frame
                tf.word_wrap = True
                for i, item in enumerate(items):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    p.text = f"• {str(item)}"
                    p.font.size = Pt(20)
                    p.font.color.rgb = rgb(c['ink'])
                    p.space_after = Pt(10)

            # 팁/경고
            tip = data.get('TIP', '')
            warning = data.get('WARNING', '')
            note_text = ''
            if tip:
                note_text = f"💡 {tip}"
            if warning:
                note_text = f"⚠️ {warning}"
            if note_text:
                note_box = slide.shapes.add_textbox(Inches(0.9), Inches(5.8), Inches(5.5), Inches(0.8))
                np = note_box.text_frame.paragraphs[0]
                np.text = note_text
                np.font.size = Pt(16)
                np.font.color.rgb = rgb(c['accent'])

            # 우측: 스크린샷 이미지
            img_src = data.get('IMAGE_SRC')
            if img_src:
                img_path = os.path.join(html_dir, img_src)
                if os.path.exists(img_path):
                    try:
                        slide.shapes.add_picture(img_path, Inches(7.0), Inches(1.2), width=Inches(5.5))
                    except Exception:
                        pass

        elif stype == 'hands_on':
            # 스텝퍼가 있으면 스텝퍼를 대제목으로 사용
            stepper_items = data.get('STEPPER_ITEMS', [])
            if stepper_items:
                stepper_text_parts = []
                for idx, step in enumerate(stepper_items):
                    label = step.get('label', f'Step {idx+1}')
                    state = step.get('state', 'inactive')
                    if isinstance(step, str):
                        label = step
                        state = 'inactive'
                    marker = '●' if state == 'active' else ('✓' if state == 'completed' else '○')
                    stepper_text_parts.append(f"{marker} {label}")
                stepper_box = slide.shapes.add_textbox(Inches(0.9), Inches(0.9), Inches(11.5), Inches(0.5))
                sp = stepper_box.text_frame.paragraphs[0]
                sp.text = "  ─  ".join(stepper_text_parts)
                sp.font.size = Pt(20) # 스텝퍼 격상
                sp.font.color.rgb = rgb(c['muted'])
                sp.font.bold = True
                sp.alignment = PP_ALIGN.LEFT

                # 원래 제목은 부제목으로
                title_box = slide.shapes.add_textbox(Inches(0.9), Inches(1.5), Inches(5.5), Inches(0.4))
                title_box.text_frame.word_wrap = False
                tp = title_box.text_frame.paragraphs[0]
                tp.text = data.get('TITLE', '')
                tp.font.size = Pt(24)
                tp.font.color.rgb = rgb(c['ink'])
            else:
                # 스텝퍼가 없을 때 기존 디자인 유지
                badge_box = slide.shapes.add_textbox(Inches(0.9), Inches(0.85), Inches(1.55), Inches(0.45))
                bp = badge_box.text_frame.paragraphs[0]
                bp.text = "실습 시간"
                bp.alignment = PP_ALIGN.CENTER
                bp.font.size = Pt(16)
                bp.font.bold = True
                bp.font.color.rgb = rgb(c['accent'])

                title_box = slide.shapes.add_textbox(Inches(2.65), Inches(0.78), Inches(9.75), Inches(0.65))
                title_box.text_frame.word_wrap = False
                tp = title_box.text_frame.paragraphs[0]
                tp.text = data.get('TITLE', '')
                tp.font.size = Pt(40 if len(tp.text) <= 14 else 36)
                tp.font.bold = True
                tp.font.color.rgb = rgb(c['ink'])

            # 좌측: 실습 순서
            label_box = slide.shapes.add_textbox(Inches(0.9), Inches(2.2), Inches(5.5), Inches(0.5))
            lp = label_box.text_frame.paragraphs[0]
            lp.text = "📋 실습 순서"
            lp.font.size = Pt(24)
            lp.font.bold = True
            lp.font.color.rgb = rgb(c['ink'])

            items = data.get('BULLET_ITEMS', [])
            if items:
                box_items = slide.shapes.add_textbox(Inches(0.9), Inches(2.9), Inches(5.5), Inches(4.0))
                tf = box_items.text_frame
                tf.word_wrap = True
                for i, item in enumerate(items):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    p.text = f"{i+1}. {str(item)}"
                    p.font.size = Pt(24)
                    p.font.color.rgb = rgb(c['ink'])
                    p.space_after = Pt(10)

            # 소요 시간
            duration = data.get('DURATION', '')
            if duration:
                d_box = slide.shapes.add_textbox(Inches(0.9), Inches(6.5), Inches(5.5), Inches(0.5))
                dp = d_box.text_frame.paragraphs[0]
                dp.text = f"⏱️ 예상 소요 시간: {duration}"
                dp.font.size = Pt(16)
                dp.font.color.rgb = rgb(c['muted'])

            # 우측: 예상 결과
            result_label = slide.shapes.add_textbox(Inches(7.0), Inches(2.2), Inches(5.5), Inches(0.5))
            rlp = result_label.text_frame.paragraphs[0]
            rlp.text = "✅ 예상 결과"
            rlp.font.size = Pt(20)
            rlp.font.bold = True
            rlp.font.color.rgb = rgb(c['ink'])

            img_src = data.get('IMAGE_SRC')
            if img_src:
                img_path = os.path.join(html_dir, img_src)
                if os.path.exists(img_path):
                    try:
                        slide.shapes.add_picture(img_path, Inches(7.0), Inches(2.9), width=Inches(5.5))
                    except Exception:
                        pass
            elif data.get('RESULT_TEXT'):
                rt_box = slide.shapes.add_textbox(Inches(7.0), Inches(2.9), Inches(5.5), Inches(4.0))
                rtp = rt_box.text_frame.paragraphs[0]
                rtp.text = data['RESULT_TEXT']
                rtp.font.size = Pt(20)
                rtp.font.color.rgb = rgb(c['ink'])

        elif stype == 'fullbleed':
            # 풀블리드: 배경 이미지 + 오버레이 텍스트
            img_src = data.get('IMAGE_SRC')
            if img_src:
                img_path = os.path.join(html_dir, img_src)
                if os.path.exists(img_path):
                    try:
                        slide.shapes.add_picture(img_path, Inches(0), Inches(0),
                                                 width=Inches(13.333), height=Inches(7.5))
                    except Exception:
                        pass

            # 스텝퍼가 있을 경우 최상단에 배치
            stepper_items = data.get('STEPPER_ITEMS', [])
            if stepper_items:
                stepper_text_parts = []
                for idx, step in enumerate(stepper_items):
                    label = step.get('label', f'Step {idx+1}')
                    state = step.get('state', 'inactive')
                    if isinstance(step, str):
                        label = step
                        state = 'inactive'
                    marker = '●' if state == 'active' else ('✓' if state == 'completed' else '○')
                    stepper_text_parts.append(f"{marker} {label}")
                stepper_box = slide.shapes.add_textbox(Inches(0.9), Inches(0.4), Inches(11.5), Inches(0.5))
                sp = stepper_box.text_frame.paragraphs[0]
                sp.text = "  ─  ".join(stepper_text_parts)
                sp.font.size = Pt(20)
                sp.font.color.rgb = RGBColor(255, 255, 255)
                sp.font.bold = True
                sp.alignment = PP_ALIGN.CENTER

            # 반투명 오버레이 (하단)
            from pptx.enum.shapes import MSO_SHAPE
            overlay = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(4.5),
                                             Inches(13.333), Inches(3.0))
            overlay.fill.solid()
            overlay.fill.fore_color.rgb = RGBColor(0, 0, 0)
            # python-pptx에서 투명도는 직접 설정 어려우므로 반투명 색상으로 대체
            overlay.line.fill.background()

            # 텍스트
            title_box = slide.shapes.add_textbox(Inches(1.5), Inches(5.0), Inches(10.3), Inches(1.5))
            tp = title_box.text_frame.paragraphs[0]
            tp.text = data.get('TITLE', '')
            tp.font.size = Pt(54)
            tp.font.bold = True
            tp.font.color.rgb = RGBColor(255, 255, 255)

            if data.get('SUBTITLE'):
                sub_p = title_box.text_frame.add_paragraph()
                sub_p.text = data['SUBTITLE']
                sub_p.font.size = Pt(32)
                sub_p.font.color.rgb = RGBColor(220, 220, 220)

    # 모든 슬라이드의 모든 텍스트 상자에 AutoFit 적용 (사용자 요청: 교육용 최대 확대/맞춤)
    for s in prs.slides:
        for shape in s.shapes:
            if shape.has_text_frame:
                shape.text_frame.word_wrap = True
                shape.text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

    # 출력 폴더 생성
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    prs.save(output_path)
    print(f"[SUCCESS] 네이티브 PPTX 변환 완료: {output_path}")
    print(f"   슬라이드 수: {len(slides_data)}장")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("사용법: python export_pptx.py <입력_json> <출력.pptx> [html디렉토리(이미지상대경로용)]")
        sys.exit(1)

    html_dir = sys.argv[3] if len(sys.argv) > 3 else None
    export_pptx(sys.argv[1], sys.argv[2], html_dir)
