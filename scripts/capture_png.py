import asyncio
import os
import sys
from pathlib import Path

from playwright.async_api import async_playwright


VIEWPORT = {"width": 1280, "height": 720}


async def wait_for_reveal(page):
    await page.wait_for_function("window.Reveal && Reveal.isReady && Reveal.isReady()")
    await page.evaluate("document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()")
    await page.wait_for_timeout(500)


async def prepare_clean_capture(page):
    await page.add_style_tag(content="""
        .review-toggle-fab,
        .timer-toggle-fab,
        .help-toggle-fab,
        body > [class*="fab"],
        .timer-modal-overlay,
        .lightbox-overlay,
        .reveal .controls,
        .reveal .progress,
        .reveal .slide-number {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
        }
        html, body {
            width: 1280px !important;
            height: 720px !important;
            overflow: hidden !important;
            background: var(--color-bg, #fff) !important;
        }
    """)
    await page.evaluate("""
        if (window.Reveal) {
            Reveal.configure({
                controls: false,
                progress: false,
                slideNumber: false,
                hash: false,
                transition: 'none',
                backgroundTransition: 'none'
            });
            Reveal.layout();
        }
    """)


async def capture_pngs(html_path, out_dir):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for stale_file in out_path.glob("slide-*.png"):
        stale_file.unlink()

    html_url = Path(html_path).resolve().as_uri()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport=VIEWPORT, device_scale_factor=1)
        await page.goto(html_url, wait_until="domcontentloaded")
        await wait_for_reveal(page)
        await prepare_clean_capture(page)

        total = await page.evaluate("Reveal.getSlides().length")
        captured = 0

        for index in range(total):
            out_file = out_path / f"slide-{index + 1:03d}.png"
            await page.evaluate("""(index) => {
                const slide = Reveal.getSlides()[index];
                const indices = Reveal.getIndices(slide);
                Reveal.slide(indices.h, indices.v, indices.f || 0);
                Reveal.layout();
            }""", index)
            await page.wait_for_timeout(350)
            
            is_worksheet = await page.evaluate("""(index) => {
                const slide = Reveal.getSlides()[index];
                return slide.querySelector('.worksheet-page') !== null;
            }""", index)
            
            if is_worksheet:
                # Resize Playwright Viewport so Chromium renders the entire height natively!
                await page.set_viewport_size({"width": 1280, "height": 1200})
                await page.wait_for_timeout(100)
                
                # Remove transform and margin for high-res crop
                await page.evaluate("""(index) => {
                    const slide = Reveal.getSlides()[index];
                    const ws = slide.querySelector('.worksheet-page');
                    
                    ws.dataset.origTransform = ws.style.transform || '';
                    ws.dataset.origMargin = ws.style.margin || '';
                    ws.style.setProperty('transform', 'none', 'important');
                    ws.style.setProperty('margin', '0', 'important');
                    
                    // Prevent centering
                    slide.dataset.origTop = slide.style.top || '';
                    slide.style.setProperty('top', '0', 'important');
                    slide.style.setProperty('height', 'auto', 'important');
                }""", index)
                
                await page.wait_for_timeout(200)
                
                element = await page.evaluate_handle("""(index) => {
                    return Reveal.getSlides()[index].querySelector('.worksheet-page');
                }""", index)
                await element.screenshot(path=str(out_file))
                
                # Restore
                await page.evaluate("""(index) => {
                    const slide = Reveal.getSlides()[index];
                    const ws = slide.querySelector('.worksheet-page');
                    ws.style.transform = ws.dataset.origTransform;
                    ws.style.margin = ws.dataset.origMargin;
                    
                    slide.style.top = slide.dataset.origTop;
                }""", index)
                
                # Revert Viewport
                await page.set_viewport_size({"width": 1280, "height": 720})
                await page.wait_for_timeout(100)
            else:
                await page.screenshot(path=str(out_file), full_page=False, animations="disabled")
            
            print(f"[CAPTURE] Slide-{index + 1:03d}: {out_file}")
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
