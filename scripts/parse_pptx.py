#!/usr/bin/env python3
"""PPTX 파일에서 텍스트를 추출하여 마크다운 파일로 저장하는 스크립트.

사용법:
    python parse_pptx.py <입력.pptx> <출력.md>

의존성:
    pip install python-pptx
"""

import sys
import os

def parse_pptx(input_path: str, output_path: str) -> None:
    """PPTX 파일에서 텍스트를 추출하여 마크다운으로 저장합니다."""
    try:
        from pptx import Presentation
    except ImportError:
        print("오류: python-pptx가 설치되지 않았습니다.")
        print("설치 명령: pip install python-pptx")
        sys.exit(1)

    if not os.path.exists(input_path):
        print(f"오류: 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    prs = Presentation(input_path)
    lines = []
    lines.append(f"# PPTX 추출: {os.path.basename(input_path)}\n")
    lines.append(f"> 원본 파일: `{input_path}`\n")
    lines.append("---\n")

    for slide_num, slide in enumerate(prs.slides, 1):
        lines.append(f"## 슬라이드 {slide_num}\n")

        for shape in slide.shapes:
            # 텍스트가 있는 도형 처리
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        # 첫 번째 텍스트 프레임의 첫 문단은 제목일 가능성이 높음
                        lines.append(f"- {text}\n")

            # 표 처리
            if shape.has_table:
                table = shape.table
                lines.append("\n| " + " | ".join(
                    cell.text.strip() for cell in table.rows[0].cells
                ) + " |")
                lines.append("| " + " | ".join(
                    "---" for _ in table.rows[0].cells
                ) + " |")
                for row in table.rows[1:]:
                    lines.append("| " + " | ".join(
                        cell.text.strip() for cell in row.cells
                    ) + " |")
                lines.append("")

        # 발표자 노트 추출
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes_text = slide.notes_slide.notes_text_frame.text.strip()
            if notes_text:
                lines.append(f"\n> **발표자 노트**: {notes_text}\n")

        lines.append("---\n")

    # 출력 폴더 생성
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ 추출 완료: {output_path}")
    print(f"   슬라이드 수: {len(prs.slides)}장")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python parse_pptx.py <입력.pptx> <출력.md>")
        sys.exit(1)

    parse_pptx(sys.argv[1], sys.argv[2])
