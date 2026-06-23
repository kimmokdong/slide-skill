#!/usr/bin/env python3
"""Mermaid 코드를 SVG 이미지로 렌더링하는 스크립트.

사용법:
    python render_mermaid.py <입력.mmd> <출력.svg>
    또는
    echo "flowchart LR; A-->B" | python render_mermaid.py --stdin <출력.svg>

의존성 (택 1):
    방법 1: npm install -g @mermaid-js/mermaid-cli
    방법 2: pip install playwright && playwright install chromium
"""

import sys
import os
import subprocess
import tempfile
import shutil


def render_with_mmdc(input_path: str, output_path: str) -> bool:
    """mermaid-cli (mmdc)를 사용하여 렌더링합니다."""
    mmdc_path = shutil.which("mmdc")
    if not mmdc_path:
        # Windows에서 npx로 시도
        try:
            result = subprocess.run(
                ["npx", "-y", "@mermaid-js/mermaid-cli", "-i", input_path, "-o", output_path, "-b", "transparent"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and os.path.exists(output_path):
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return False

    try:
        result = subprocess.run(
            [mmdc_path, "-i", input_path, "-o", output_path, "-b", "transparent"],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0 and os.path.exists(output_path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def render_with_playwright(mermaid_code: str, output_path: str) -> bool:
    """Playwright를 사용하여 브라우저에서 렌더링합니다."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head>
<body>
    <div class="mermaid" id="diagram">
{mermaid_code}
    </div>
    <script>
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</body>
</html>"""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # HTML을 임시 파일로 저장
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_html = f.name

            page.goto(f"file://{temp_html}")
            page.wait_for_selector(".mermaid svg", timeout=10000)

            # SVG 추출
            svg_content = page.eval_on_selector(".mermaid", "el => el.innerHTML")

            browser.close()
            os.unlink(temp_html)

            # SVG 파일 저장
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(svg_content)

            return True
    except Exception:
        return False


def render_mermaid(input_path: str, output_path: str) -> None:
    """Mermaid 코드를 SVG로 렌더링합니다."""

    if not os.path.exists(input_path):
        print(f"오류: 파일을 찾을 수 없습니다: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        mermaid_code = f.read().strip()

    if not mermaid_code:
        print("오류: Mermaid 코드가 비어있습니다.")
        sys.exit(1)

    # 출력 폴더 생성
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # 방법 1: mermaid-cli (mmdc) 시도
    print("🔄 mermaid-cli(mmdc)로 렌더링 시도...")
    if render_with_mmdc(input_path, output_path):
        print(f"✅ SVG 렌더링 완료 (mmdc): {output_path}")
        return

    # 방법 2: Playwright 시도
    print("🔄 Playwright로 렌더링 시도...")
    if render_with_playwright(mermaid_code, output_path):
        print(f"✅ SVG 렌더링 완료 (Playwright): {output_path}")
        return

    # 모두 실패
    print("❌ SVG 렌더링 실패. 아래 도구 중 하나를 설치해주세요:")
    print("   방법 1: npm install -g @mermaid-js/mermaid-cli")
    print("   방법 2: pip install playwright && playwright install chromium")
    sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] != "--stdin":
        render_mermaid(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 3 and sys.argv[1] == "--stdin":
        # stdin에서 읽기
        mermaid_code = sys.stdin.read().strip()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False, encoding='utf-8') as f:
            f.write(mermaid_code)
            temp_input = f.name
        try:
            render_mermaid(temp_input, sys.argv[2])
        finally:
            os.unlink(temp_input)
    else:
        print("사용법:")
        print("  python render_mermaid.py <입력.mmd> <출력.svg>")
        print("  echo 'flowchart LR; A-->B' | python render_mermaid.py --stdin <출력.svg>")
        sys.exit(1)
