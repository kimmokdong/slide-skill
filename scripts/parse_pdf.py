#!/usr/bin/env python3
"""PDF 파일에서 텍스트를 추출하여 마크다운 파일로 저장하는 스크립트.

사용법:
    python parse_pdf.py <입력.pdf> <출력.md>

의존성:
    pip install pdfplumber
"""

import sys
import os

def parse_pdf(input_path: str, output_path: str) -> None:
    """PDF 파일에서 텍스트를 추출하여 마크다운으로 저장합니다."""
    try:
        import pdfplumber
    except ImportError:
        print("오류: pdfplumber가 설치되지 않았습니다.")
        print("설치 명령: pip install pdfplumber")
        sys.exit(1)

    if not os.path.exists(input_path):
        print(f"오류: 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    lines = []
    lines.append(f"# PDF 추출: {os.path.basename(input_path)}\n")
    lines.append(f"> 원본 파일: `{input_path}`\n")
    lines.append("---\n")

    with pdfplumber.open(input_path) as pdf:
        total_pages = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, 1):
            lines.append(f"## 페이지 {page_num}\n")

            # 텍스트 추출
            text = page.extract_text()
            if text:
                # 각 줄을 정리하여 추가
                for line in text.split("\n"):
                    stripped = line.strip()
                    if stripped:
                        lines.append(f"{stripped}\n")

            # 표 추출
            tables = page.extract_tables()
            if tables:
                for table_idx, table in enumerate(tables):
                    if table and len(table) > 0:
                        lines.append(f"\n**표 {table_idx + 1}:**\n")
                        # 헤더
                        header = table[0]
                        lines.append("| " + " | ".join(
                            str(cell or "").strip() for cell in header
                        ) + " |")
                        lines.append("| " + " | ".join(
                            "---" for _ in header
                        ) + " |")
                        # 데이터 행
                        for row in table[1:]:
                            lines.append("| " + " | ".join(
                                str(cell or "").strip() for cell in row
                            ) + " |")
                        lines.append("")

            lines.append("---\n")

    # 출력 폴더 생성
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ 추출 완료: {output_path}")
    print(f"   페이지 수: {total_pages}페이지")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python parse_pdf.py <입력.pdf> <출력.md>")
        sys.exit(1)

    parse_pdf(sys.argv[1], sys.argv[2])
