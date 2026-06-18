import sys
import os
import asyncio
from playwright.async_api import async_playwright

async def capture_pngs(html_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    html_url = f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}?print-pdf"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 16:9 해상도 설정
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.goto(html_url, wait_until="networkidle")
        
        # 슬라이드 요소 찾기 (.slide-container를 감싸는 section 캡처)
        slides = await page.query_selector_all("section")
        count = 0
        for slide in slides:
            # Reveal.js의 pdf 모드에서는 숨겨진 section이나 빈 section이 있을 수 있으므로 필터링
            bbox = await slide.bounding_box()
            if bbox and bbox['width'] > 0 and bbox['height'] > 0:
                out_file = os.path.join(out_dir, f"slide-{count+1:03d}.png")
                await slide.screenshot(path=out_file)
                print(f"[CAPTURE] Slide-{count+1:03d}: {out_file}")
                count += 1
            
        await browser.close()
        print(f"[SUCCESS] Captured total {count} slides!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python capture_png.py <input_html> <output_dir>")
        sys.exit(1)
    asyncio.run(capture_pngs(sys.argv[1], sys.argv[2]))
