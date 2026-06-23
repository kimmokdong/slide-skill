#!/usr/bin/env python3
"""HTML 슬라이드를 PDF로 변환하는 스크립트.

사용법:
    python export_pdf.py <입력.html> <출력.pdf>

의존성:
    pip install playwright
    playwright install chromium
"""

import sys
import os


def export_pdf(input_path: str, output_path: str) -> None:
    """Playwright를 사용하여 HTML을 PDF로 변환합니다."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("오류: playwright가 설치되지 않았습니다.")
        print("설치 명령:")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    if not os.path.exists(input_path):
        print(f"오류: 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    # 출력 폴더 생성
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    abs_input = os.path.abspath(input_path)
    file_url = f"file:///{abs_input.replace(os.sep, '/')}"

    print(f"🔄 PDF 변환 중: {input_path}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        # Reveal.js 슬라이드 로드
        page.goto(file_url, wait_until="networkidle")
        page.wait_for_timeout(3000)  # Reveal.js 초기화 대기

        # Reveal.js를 인쇄 모드로 전환
        # ?print-pdf 쿼리를 추가하면 Reveal.js가 인쇄 모드로 전환됨
        print_url = f"{file_url}?print-pdf"
        page.goto(print_url, wait_until="networkidle")
        page.wait_for_timeout(5000)  # 인쇄 모드 렌더링 대기

        # PDF 생성 (가로 모드, 16:9 비율)
        page.pdf(
            path=output_path,
            format="A4",
            landscape=True,
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )

        browser.close()

    print(f"✅ PDF 변환 완료: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("사용법: python export_pdf.py <입력.html> <출력.pdf>")
        sys.exit(1)

    export_pdf(sys.argv[1], sys.argv[2])
