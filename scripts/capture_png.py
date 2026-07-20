import asyncio
import json
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
        .review-sidebar,
        .reveal .controls,
        .reveal .progress,
        .reveal .slide-number {
            display: none !important;
            opacity: 0 !important;
            visibility: hidden !important;
        }
        .reveal .slides section .fragment {
            opacity: 1 !important;
            visibility: visible !important;
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
        document.body.classList.add('static-export');
        document.querySelectorAll('.fragment').forEach(el => el.classList.add('visible'));
        document.querySelectorAll('.quiz-option[data-correct="true"]').forEach(el => {
            el.classList.add('quiz-correct');
        });
    """)


async def prepare_static_slide(page, index):
    await page.evaluate("""(index) => {
        const slide = Reveal.getSlides()[index];
        slide.querySelectorAll('.fragment').forEach(el => el.classList.add('visible'));
        slide.querySelectorAll('.quiz-option[data-correct="true"]').forEach(el => {
            el.classList.add('quiz-correct');
        });
        slide.querySelectorAll('.js-cloze-target').forEach(target => {
            target.textContent = target.dataset.word || '';
            target.classList.add('is-filled');
        });
        slide.querySelectorAll('.js-cloze-word').forEach(word => word.classList.add('is-used'));

        slide.querySelectorAll('.js-match-anim').forEach(group => {
            const start = slide.querySelector(group.dataset.start);
            const end = slide.querySelector(group.dataset.end);
            const container = group.closest('.matching-columns-container');
            const path = group.querySelector('.match-svg-line');
            const arrow = group.querySelector('.match-svg-arrowhead');
            if (!start || !end || !container || !path || !arrow) return;

            const box = container.getBoundingClientRect();
            const startBox = start.getBoundingClientRect();
            const endBox = end.getBoundingClientRect();
            const startX = startBox.left - box.left + startBox.width / 2;
            const startY = startBox.top - box.top + startBox.height / 2;
            const endX = endBox.left - box.left + endBox.width / 2;
            const endY = endBox.top - box.top + endBox.height / 2;
            const angle = Math.atan2(endY - startY, endX - startX) * 180 / Math.PI;
            path.setAttribute('d', `M${startX},${startY} L${endX},${endY}`);
            arrow.setAttribute('points', '-16,-10 6,0 -16,10');
            arrow.setAttribute('transform', `translate(${endX}, ${endY}) rotate(${angle})`);
        });

        const container = slide.querySelector('.slide-container, .center-layout');
        if (container && typeof window.stabilizeSlideContainerShrinkOnly === 'function') {
            window.stabilizeSlideContainerShrinkOnly(container, { preserveEditedText: true });
            Reveal.layout();
        }
    }""", index)


async def audit_slide(page, index):
    return await page.evaluate(r"""(index) => {
        const slide = Reveal.getSlides()[index];
        const layout = slide.dataset.layoutName || slide.dataset.pageType || 'unknown';
        const root = slide.querySelector('.slide-container, .center-layout, .worksheet-page');
        if (!root) {
            return { slide: index + 1, layout, issues: [] };
        }

        const issues = [];
        const rootBox = root.getBoundingClientRect();
        const visible = el => {
            const style = getComputedStyle(el);
            const box = el.getBoundingClientRect();
            return style.display !== 'none' && style.visibility !== 'hidden' && box.width > 0 && box.height > 0;
        };
        const add = (severity, code, el, detail) => issues.push({
            severity,
            code,
            target: el?.dataset?.editId || el?.className || el?.tagName || 'slide',
            detail
        });
        const hasDirectText = el => Array.from(el.childNodes).some(node =>
            node.nodeType === Node.TEXT_NODE && node.textContent.trim()
        );
        const scrollBoxOverflows = (el, style = getComputedStyle(el)) => {
            const fontSize = parseFloat(style.fontSize) || 16;
            const verticalTolerance = Math.max(4, fontSize * 0.65);
            const horizontalTolerance = Math.max(3, fontSize * 0.18);
            return (
                (style.overflowY !== 'visible' && el.scrollHeight > el.clientHeight + verticalTolerance) ||
                (style.overflowX !== 'visible' && el.scrollWidth > el.clientWidth + horizontalTolerance)
            );
        };
        const clippingAncestor = el => {
            const contentBox = el.getBoundingClientRect();
            let current = el;
            while (current && root.contains(current)) {
                const style = getComputedStyle(current);
                const clipsX = style.overflowX !== 'visible';
                const clipsY = style.overflowY !== 'visible';
                if (clipsX || clipsY) {
                    const box = current.getBoundingClientRect();
                    const ownOverflow = current === el && scrollBoxOverflows(el, style);
                    const ancestorOverflow = current !== el && (
                        (clipsY && (contentBox.top < box.top - 2 || contentBox.bottom > box.bottom + 2)) ||
                        (clipsX && (contentBox.left < box.left - 2 || contentBox.right > box.right + 2))
                    );
                    if (ownOverflow || ancestorOverflow) {
                        return current;
                    }
                }
                if (current === root) break;
                current = current.parentElement;
            }
            return null;
        };

        if (root.classList.contains('worksheet-page')) {
            const body = root.querySelector('.worksheet-page-body');
            if (body && body.scrollHeight > body.clientHeight + 2) {
                add('error', 'worksheet-overflow', body, '학습지 내용이 페이지 높이를 초과합니다.');
            }
            return { slide: index + 1, layout, issues };
        }

        const textTargets = Array.from(root.querySelectorAll('*')).filter(el =>
            visible(el) &&
            hasDirectText(el) &&
            !el.closest('aside.notes') &&
            !el.matches('script, style')
        );

        textTargets.forEach(el => {
            const box = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            const fontSize = parseFloat(style.fontSize) || 0;
            const lineHeight = parseFloat(style.lineHeight);
            const clipper = clippingAncestor(el);
            if (clipper && !el.closest('.ox-reveal-answer')) {
                const clipperName = clipper.dataset.editId || clipper.className || clipper.tagName;
                add('error', 'text-overflow', el, `${clipperName} 영역에서 텍스트가 잘립니다.`);
            }
            if (box.left < rootBox.left - 2 || box.top < rootBox.top - 2 || box.right > rootBox.right + 2 || box.bottom > rootBox.bottom + 2) {
                add('error', 'off-slide', el, '텍스트가 슬라이드 영역을 벗어났습니다.');
            }
            if (fontSize && fontSize < 18) {
                add('error', 'small-text', el, `글자 크기 ${fontSize.toFixed(1)}px`);
            }
            const compactFixedUi = el.closest([
                '.roadmap-num',
                '.timeline-marker',
                '.stepper-step',
                '.option-marker',
                '.step-num',
                '.ox-marker',
                '.ox-header-marker',
                '.ox-reveal-answer',
                '.placeholder-label',
                '.summary-emoji',
                '.activity-timer',
                '.activity-think-question > span',
                '.cloze-word',
                '.reveal-table th',
                '.reveal-table td'
            ].join(','));
            if (fontSize && Number.isFinite(lineHeight) && !compactFixedUi) {
                const ratio = lineHeight / fontSize;
                if (ratio < 1.05 || ratio > 1.8) {
                    add('warning', 'line-height', el, `line-height 비율 ${ratio.toFixed(2)}`);
                }
            }
        });

        root.querySelectorAll('.roadmap-num, .timeline-marker, .option-marker, .step-num').forEach(el => {
            if (!visible(el)) return;
            const box = el.getBoundingClientRect();
            if (Math.abs(box.width - box.height) > 2) {
                add('error', 'shape-distorted', el, `${box.width.toFixed(1)}x${box.height.toFixed(1)}px`);
            }
        });

        const placeholder = root.textContent.match(/\{\{[^{}]+\}\}|<TODO>|\blorem\b|\bxxxx\b/i);
        if (placeholder) add('error', 'placeholder', root, `남은 토큰: ${placeholder[0]}`);

        const hasGeometryError = issues.some(issue =>
            issue.severity === 'error' && ['text-overflow', 'off-slide', 'shape-distorted'].includes(issue.code)
        );
        const rootOverflows = Array.from(root.children).some(child => {
            if (!visible(child) || child.matches('aside.notes')) return false;
            const box = child.getBoundingClientRect();
            return box.left < rootBox.left - 2 || box.top < rootBox.top - 2 ||
                box.right > rootBox.right + 2 || box.bottom > rootBox.bottom + 2;
        });
        if (rootOverflows) {
            add(
                'error',
                'layout-overflow',
                root,
                '슬라이드의 직접 콘텐츠가 루트 영역을 초과합니다.'
            );
        }
        if (
            (root.dataset.autofitFailed === 'true' || root.classList.contains('autofit-failed')) &&
            (hasGeometryError || rootOverflows)
        ) {
            add('error', 'autofit-failed', root, '최소 글자 크기에서도 영역을 넘칩니다.');
        }

        return { slide: index + 1, layout, issues };
    }""", index)


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
        audit_results = []

        for index in range(total):
            out_file = out_path / f"slide-{index + 1:03d}.png"
            await page.evaluate("""(index) => {
                const slide = Reveal.getSlides()[index];
                const indices = Reveal.getIndices(slide);
                Reveal.slide(indices.h, indices.v, indices.f || 0);
                Reveal.layout();
            }""", index)
            await page.wait_for_timeout(350)
            await prepare_static_slide(page, index)
            await page.wait_for_timeout(50)
            audit_results.append(await audit_slide(page, index))
            
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
                    slide.dataset.origTransform = slide.style.transform || '';
                    slide.style.setProperty('top', '0', 'important');
                    slide.style.setProperty('transform', 'none', 'important');
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
                    slide.style.transform = slide.dataset.origTransform;
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

    issues = [issue for result in audit_results for issue in result['issues']]
    report = {
        'html': str(Path(html_path).resolve()),
        'slides': audit_results,
        'summary': {
            'slides': captured,
            'errors': sum(issue['severity'] == 'error' for issue in issues),
            'warnings': sum(issue['severity'] == 'warning' for issue in issues),
        },
    }
    report_path = out_path / 'qa-report.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[QA] DOM report: {report_path} ({report['summary']['errors']} errors, {report['summary']['warnings']} warnings)")

    if report['summary']['errors']:
        raise RuntimeError(f"HTML Slide QA failed: {report['summary']['errors']} errors. See {report_path}")

    print(f"[SUCCESS] Captured total {captured} slides!")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python capture_png.py <input_html> <output_dir>")
        sys.exit(1)
    asyncio.run(capture_pngs(sys.argv[1], sys.argv[2]))
