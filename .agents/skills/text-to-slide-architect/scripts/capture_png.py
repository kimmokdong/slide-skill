import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import async_playwright


async def capture_slide(locator, out_file):
    for attempt in range(3):
        try:
            bbox = await locator.bounding_box()
            if not bbox or bbox["width"] <= 0 or bbox["height"] <= 0:
                return False
            await locator.screenshot(path=out_file, animations="disabled")
            return True
        except PlaywrightError as exc:
            if attempt == 2:
                print(f"[WARN] Skipped unstable slide: {exc}")
                return False
            await locator.page.wait_for_timeout(250)
    return False


async def capture_pngs(html_path, out_dir):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for stale_file in out_path.glob("slide-*.png"):
        stale_file.unlink()

    html_url = f"file:///{os.path.abspath(html_path).replace(os.sep, '/')}?print-pdf"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.goto(html_url, wait_until="networkidle")
        await page.wait_for_timeout(750)

        slides = page.locator("section")
        total = await slides.count()
        captured = 0

        for index in range(total):
            out_file = out_path / f"slide-{captured + 1:03d}.png"
            if await capture_slide(slides.nth(index), str(out_file)):
                print(f"[CAPTURE] Slide-{captured + 1:03d}: {out_file}")
                captured += 1

        await browser.close()

    if captured == 0:
        raise RuntimeError("No visible slides were captured.")

    print(f"[SUCCESS] Captured total {captured} slides!")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python capture_png.py <input_html> <output_dir>")
        sys.exit(1)
    asyncio.run(capture_pngs(sys.argv[1], sys.argv[2]))
