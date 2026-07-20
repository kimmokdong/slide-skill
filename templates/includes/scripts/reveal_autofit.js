        Reveal.initialize({
            hash: true,
            slideNumber: 'c/t',
            showSlideNumber: 'all',
            transition: 'slide',
            transitionSpeed: 'default',
            backgroundTransition: 'fade',
            center: false,
            width: 1280,
            height: 720,
            margin: 0,
            minScale: 0.2,
            maxScale: 2.0,
            plugins: [ RevealNotes ]
        });

        function cssNumber(el, name, fallback) {
            const raw = getComputedStyle(el).getPropertyValue(name).trim();
            const parsed = parseFloat(raw);
            return Number.isFinite(parsed) ? parsed : fallback;
        }

        function hasLayoutBox(el) {
            const style = getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            const rect = el.getBoundingClientRect();
            if (
                el.clientWidth <= 0 &&
                el.clientHeight <= 0 &&
                rect.width <= 0 &&
                rect.height <= 0
            ) {
                return false;
            }
            return true;
        }

        function scrollBoxOverflows(el, style = getComputedStyle(el)) {
            const fontSize = parseFloat(style.fontSize) || 16;
            const verticalTolerance = Math.max(4, fontSize * 0.65);
            const horizontalTolerance = Math.max(3, fontSize * 0.18);
            return (
                (style.overflowY !== 'visible' && el.scrollHeight > el.clientHeight + verticalTolerance) ||
                (style.overflowX !== 'visible' && el.scrollWidth > el.clientWidth + horizontalTolerance)
            );
        }

        function elementOverflows(el, boundary) {
            if (!hasLayoutBox(el)) return false;
            const style = getComputedStyle(el);
            if (style.position === 'absolute' || style.position === 'fixed') return false;

            const rect = el.getBoundingClientRect();
            const boundaryRect = boundary.getBoundingClientRect();
            const boxOverflow = scrollBoxOverflows(el, style);
            const boundaryOverflow =
                rect.left < boundaryRect.left - 2 ||
                rect.top < boundaryRect.top - 2 ||
                rect.right > boundaryRect.right + 2 ||
                rect.bottom > boundaryRect.bottom + 2;

            let ancestor = el.parentElement;
            let ancestorOverflow = false;
            while (ancestor && boundary.contains(ancestor)) {
                const ancestorStyle = getComputedStyle(ancestor);
                if (ancestorStyle.overflowX !== 'visible' || ancestorStyle.overflowY !== 'visible') {
                    const ancestorRect = ancestor.getBoundingClientRect();
                    ancestorOverflow =
                        (ancestorStyle.overflowY !== 'visible' && (rect.top < ancestorRect.top - 2 || rect.bottom > ancestorRect.bottom + 2)) ||
                        (ancestorStyle.overflowX !== 'visible' && (rect.left < ancestorRect.left - 2 || rect.right > ancestorRect.right + 2));
                    if (ancestorOverflow) break;
                }
                if (ancestor === boundary) break;
                ancestor = ancestor.parentElement;
            }

            return boxOverflow || boundaryOverflow || ancestorOverflow;
        }

        const MAIN_AUTOFIT_SELECTOR = '.slide-header h2, .takeaway-content';
        const FIT_TEXT_SELECTOR = '.slide-container [data-edit-id], .center-layout [data-edit-id]';
        const FIXED_UI_SELECTOR = [
            '.bullet-icon',
            '.matrix-icon',
            '.ox-marker',
            '.ox-header-marker',
            '.roadmap-num',
            '.timeline-marker',
            '.option-marker',
            '.step-num',
            '.ox-reveal-answer',
            '.duration-badge',
            '.activity-timer'
        ].join(',');
        function bodyOverflows(body) {
            if (!body) return false;
            return Array.from(body.querySelectorAll('*'))
                .filter(hasLayoutBox)
                .some(child => elementOverflows(child, body));
        }

        function fitTextTargets(container) {
            return Array.from(container.querySelectorAll(FIT_TEXT_SELECTOR)).filter(el => {
                if (!hasLayoutBox(el) || isTextSizeLocked(el) || el.closest(FIXED_UI_SELECTOR)) return false;
                if (el.closest('.slide-header, .bottom-takeaway-bar')) return false;
                if (!el.textContent || !el.textContent.trim()) return false;
                return !el.querySelector('[data-edit-id]');
            });
        }

        function restoreFitTextTarget(el) {
            if (el.dataset.fitOriginalCaptured !== 'true') {
                el.dataset.fitOriginalCaptured = 'true';
                el.dataset.fitOriginalFontSize = el.style.getPropertyValue('font-size') || '';
                el.dataset.fitOriginalFontPriority = el.style.getPropertyPriority('font-size') || '';
            }

            el.style.removeProperty('font-size');
            if (el.dataset.fitOriginalFontSize) {
                el.style.setProperty(
                    'font-size',
                    el.dataset.fitOriginalFontSize,
                    el.dataset.fitOriginalFontPriority || ''
                );
            }
        }

        function fitSplitText(container, targets) {
            const target = targets.length === 1 ? targets[0] : null;
            const boundary = container.querySelector('.split-layout .left');
            if (!target || !boundary || !target.closest('.split-layout .left')) return false;

            const base = parseFloat(getComputedStyle(target).fontSize) || 18;
            const min = Math.min(base, Math.max(18, cssNumber(target, '--autofit-min', 18)));
            const max = Math.max(base, cssNumber(target, '--autofit-max', base));
            const fits = () => {
                const textRect = target.getBoundingClientRect();
                const boundaryRect = boundary.getBoundingClientRect();
                return textRect.left >= boundaryRect.left - 2 &&
                    textRect.top >= boundaryRect.top - 2 &&
                    textRect.right <= boundaryRect.right + 2 &&
                    textRect.bottom <= boundaryRect.bottom + 2;
            };
            const apply = size => setAutofitFontSize(target, size);

            apply(min);
            if (!fits()) {
                container.classList.add('autofit-failed');
                container.dataset.autofitFailed = 'true';
                return true;
            }

            let low = min;
            let high = max;
            for (let attempt = 0; attempt < 8; attempt += 1) {
                const size = (low + high) / 2;
                apply(size);
                if (fits()) low = size;
                else high = size;
            }
            apply(low);
            return true;
        }

        function fitTextBoxes(container, options = {}) {
            const boundary = container;
            const targets = fitTextTargets(container);
            if (!boundary || !targets.length) return;

            container.classList.remove('autofit-failed');
            delete container.dataset.autofitFailed;

            if (options.reset !== false) {
                container.classList.remove('autofit-compact');
                targets.forEach(restoreFitTextTarget);
            }

            if (fitSplitText(container, targets)) return;

            const metrics = targets.map(el => {
                const base = parseFloat(getComputedStyle(el).fontSize) || 18;
                const min = Math.min(base, Math.max(18, cssNumber(el, '--autofit-min', 18)));
                const max = Math.max(base, cssNumber(el, '--autofit-max', base));
                return { el, base, min, max };
            });
            const applyScale = scale => metrics.forEach(({ el, base, min }) => {
                setAutofitFontSize(el, Math.max(min, base * scale));
            });

            if (!bodyOverflows(boundary)) return;

            container.classList.add('autofit-compact');
            if (!bodyOverflows(boundary)) return;

            applyScale(0);
            if (bodyOverflows(boundary)) {
                container.classList.add('autofit-failed');
                container.dataset.autofitFailed = 'true';
                return;
            }

            let low = 0;
            let high = 1;
            for (let attempt = 0; attempt < 8; attempt += 1) {
                const scale = (low + high) / 2;
                applyScale(scale);
                if (bodyOverflows(boundary)) high = scale;
                else low = scale;
            }
            applyScale(low);
        }

        function isTextSizeLocked(el) {
            return Boolean(el && el.dataset && el.dataset.styleLocked === 'true');
        }

        function snapshotLockedFontSizes(container) {
            return Array.from(container.querySelectorAll('[data-style-locked="true"]')).map(el => ({
                el,
                fontSize: el.style.fontSize
            }));
        }

        function restoreLockedFontSizes(snapshot) {
            snapshot.forEach(item => {
                if (item.el && item.fontSize) item.el.style.fontSize = item.fontSize;
            });
        }

        function themeBaselineTargets(container) {
            if (!container) return [];
            return Array.from(container.querySelectorAll(MAIN_AUTOFIT_SELECTOR));
        }

        function isMainAutofitTarget(el) {
            return Boolean(el && el.matches && el.matches(MAIN_AUTOFIT_SELECTOR));
        }

        function currentFontSizePx(el) {
            const value =
                parseFloat(el.style.fontSize) ||
                parseFloat(el.dataset.autofitSize) ||
                parseFloat(getComputedStyle(el).fontSize);
            return Number.isFinite(value) ? value : null;
        }

        function clearThemeAutofitBaseline(container) {
            if (!container) return;
            delete container.dataset.themeAutofitBaselineCaptured;
            themeBaselineTargets(container).forEach(el => {
                delete el.dataset.themeBaselineFontSize;
                delete el.dataset.themeBaselineInlineFontSize;
                delete el.dataset.themeBaselineInlineFontPriority;
            });
        }

        function storeThemeAutofitBaseline(container, options = {}) {
            if (!container) return;
            if (container.dataset.themeAutofitBaselineCaptured === 'true' && !options.force) return;
            themeBaselineTargets(container).forEach(el => {
                if (isTextSizeLocked(el)) return;
                el.dataset.themeBaselineInlineFontSize = el.style.getPropertyValue('font-size') || '';
                el.dataset.themeBaselineInlineFontPriority = el.style.getPropertyPriority('font-size') || '';
                const size = currentFontSizePx(el);
                if (size) el.dataset.themeBaselineFontSize = String(size);
            });
            container.dataset.themeAutofitBaselineCaptured = 'true';
        }

        function captureThemeAutofitBaseline(container) {
            if (!container || container.dataset.themeAutofitBaselineCaptured === 'true') return;
            storeThemeAutofitBaseline(container);
        }

        function restoreThemeAutofitBaseline(container) {
            themeBaselineTargets(container).forEach(el => {
                if (isTextSizeLocked(el)) return;
                const size = parseFloat(el.dataset.themeBaselineFontSize);
                if (!Object.prototype.hasOwnProperty.call(el.dataset, 'themeBaselineInlineFontSize')) return;

                el.style.removeProperty('font-size');
                if (el.dataset.themeBaselineInlineFontSize) {
                    el.style.setProperty(
                        'font-size',
                        el.dataset.themeBaselineInlineFontSize,
                        el.dataset.themeBaselineInlineFontPriority || ''
                    );
                } else if (isMainAutofitTarget(el) && Number.isFinite(size)) {
                    el.style.fontSize = size + 'px';
                }

            });
        }

        function setAutofitFontSize(el, px) {
            el.style.setProperty('font-size', px + 'px', 'important');
        }

        function withStableAutofitMeasurement(container, callback) {
            const reveal = document.querySelector('.reveal');
            if (reveal) reveal.classList.add('autofit-measuring');
            if (container) container.classList.add('autofit-measuring');

            try {
                return callback();
            } finally {
                if (container) container.classList.remove('autofit-measuring');
                if (reveal) reveal.classList.remove('autofit-measuring');
            }
        }

        
        function shrinkWorksheet() {
            document.querySelectorAll('.worksheet-page').forEach(page => {
                const body = page.querySelector('.worksheet-page-body');
                if (!body) return;
                
                // 사용자가 수동으로 잠근 폰트 크기 요소 보존
                const lockedEls = body.querySelectorAll('[data-style-locked="true"]');
                const lockedSizes = new Map();
                lockedEls.forEach(el => {
                    lockedSizes.set(el, el.style.fontSize);
                });
                
                // 측정을 위해 overflow 임시 해제
                const origOverflow = body.style.overflow;
                body.style.overflow = 'visible';
                
                // 페이지 내부 사용 가능 높이 계산
                const pageStyle = getComputedStyle(page);
                const pageHeight = page.clientHeight 
                    - parseFloat(pageStyle.paddingTop) 
                    - parseFloat(pageStyle.paddingBottom);
                const header = page.querySelector('.worksheet-page-header');
                const headerHeight = header ? header.offsetHeight + parseFloat(getComputedStyle(header).marginBottom || 0) : 0;
                const availableHeight = pageHeight - headerHeight;
                
                let currentSize = 20;
                body.style.fontSize = currentSize + 'px';
                
                // 잠긴 폰트 크기 복원
                lockedSizes.forEach((size, el) => {
                    if (size) el.style.fontSize = size;
                });
                
                // body의 scrollHeight가 사용 가능 영역을 초과하면 축소
                while (body.scrollHeight > availableHeight + 2 && currentSize > 14) {
                    currentSize -= 0.5;
                    body.style.fontSize = currentSize + 'px';
                    // 잠긴 폰트 크기 매번 재복원
                    lockedSizes.forEach((size, el) => {
                        if (size) el.style.fontSize = size;
                    });
                }
                
                body.style.overflow = origOverflow || 'hidden';
                page.classList.toggle('worksheet-overflow', body.scrollHeight > availableHeight + 2);
            });
        }

        function autoFitAllSlides(options = {}) {
            shrinkWorksheet();
            document.querySelectorAll('.slide-container, .center-layout').forEach(container => {
                autoFitContainer(container, { force: true, ...options });
            });
        }

        function fitSingleLine(el, maxVar, minVar, maxFallback, minFallback) {
            if (!el || isTextSizeLocked(el)) return;
            const maxSize = cssNumber(el, maxVar, maxFallback);
            const minSize = cssNumber(el, minVar, minFallback);
            el.style.whiteSpace = 'nowrap';
            el.style.fontSize = maxSize + 'px';

            while (
                (el.scrollWidth > el.clientWidth + 2 || el.scrollHeight > el.clientHeight + 2) &&
                parseFloat(el.style.fontSize) > minSize
            ) {
                el.style.fontSize = (parseFloat(el.style.fontSize) - 1) + 'px';
            }
        }

        function fitSingleLineShrinkOnly(el, minVar, minFallback) {
            if (!el || isTextSizeLocked(el)) return;
            const computed = getComputedStyle(el);
            const minSize = cssNumber(el, minVar, minFallback);
            let currentSize = parseFloat(el.style.fontSize) || parseFloat(computed.fontSize) || minSize;

            el.style.whiteSpace = 'nowrap';
            el.style.fontSize = currentSize + 'px';

            while (
                (el.scrollWidth > el.clientWidth + 2 || el.scrollHeight > el.clientHeight + 2) &&
                currentSize > minSize
            ) {
                currentSize -= 1;
                el.style.fontSize = currentSize + 'px';
            }
        }

        function autoFitContainer(container, options = {}) {
            if (container.dataset.autofitDone === 'true' && !options.force) return;
            
            // Fragment 임시 표시 (최종 크기 정확한 측정을 위해)
            const hiddenFragments = Array.from(container.querySelectorAll('.fragment:not(.visible)'));
            hiddenFragments.forEach(f => {
                f.style.transition = 'none';
                f.classList.add('visible', 'autofit-temp');
            });
            
            const lockedSnapshot = options.preserveEditedText ? snapshotLockedFontSizes(container) : [];

            container.querySelectorAll('.slide-header h2').forEach(h2 => {
                fitSingleLine(h2, '--title-fit-max', '--title-fit-min', 72, 34);
            });

            container.querySelectorAll('.takeaway-content').forEach(tc => {
                fitSingleLine(tc, '--takeaway-fit-max', '--takeaway-fit-min', 42, 20);
            });

            fitTextBoxes(container);
            if (options.preserveEditedText) restoreLockedFontSizes(lockedSnapshot);
            container.dataset.autofitDone = 'true';
            storeThemeAutofitBaseline(container, { force: true });
            
            // Fragment 원상 복구
            hiddenFragments.forEach(f => {
                f.classList.remove('visible', 'autofit-temp');
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        f.style.transition = '';
                    });
                });
            });
        }

        function stabilizeSlideContainer(container, options = {}) {
            if (!container) return;
            container.dataset.autofitDone = 'false';
            autoFitContainer(container, {
                force: true,
                preserveEditedText: options.preserveEditedText !== false
            });
        }

        function stabilizeSlideContainerShrinkOnly(container, options = {}) {
            if (!container) return;

            const hiddenFragments = Array.from(container.querySelectorAll('.fragment:not(.visible)'));
            hiddenFragments.forEach(f => {
                f.style.transition = 'none';
                f.classList.add('visible', 'autofit-temp');
            });

            const lockedSnapshot = options.preserveEditedText === false ? [] : snapshotLockedFontSizes(container);

            withStableAutofitMeasurement(container, () => {
                restoreThemeAutofitBaseline(container);

                container.querySelectorAll('.slide-header h2').forEach(h2 => {
                    fitSingleLineShrinkOnly(h2, '--title-fit-min', 34);
                });

                container.querySelectorAll('.takeaway-content').forEach(tc => {
                    fitSingleLineShrinkOnly(tc, '--takeaway-fit-min', 20);
                });

                fitTextBoxes(container);
                if(typeof shrinkWorksheet === 'function') shrinkWorksheet();
            });

            if (options.preserveEditedText !== false) restoreLockedFontSizes(lockedSnapshot);
            container.dataset.autofitDone = 'true';

            hiddenFragments.forEach(f => {
                f.classList.remove('visible', 'autofit-temp');
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        f.style.transition = '';
                    });
                });
            });
        }

        function captureCurrentSlideThemeAutofitBaseline() {
            const slide = Reveal.getCurrentSlide();
            const container = slide && slide.querySelector('.slide-container, .center-layout');
            captureThemeAutofitBaseline(container);
        }

        window.stabilizeSlideContainerShrinkOnly = stabilizeSlideContainerShrinkOnly;

        function stabilizeAfterPaint(container, delay = 0) {
            const run = () => {
                if (container) {
                    stabilizeSlideContainerShrinkOnly(container, { preserveEditedText: true });
                } else {
                    document.querySelectorAll('.slide-container, .center-layout').forEach(item => {
                        stabilizeSlideContainerShrinkOnly(item, { preserveEditedText: true });
                    });
                }
                Reveal.layout();
            };

            requestAnimationFrame(() => {
                requestAnimationFrame(run);
            });

            if (delay > 0) {
                setTimeout(run, delay);
            }
        }

        function stabilizeCurrentSlideAfterThemeChange() {
            const slide = Reveal.getCurrentSlide();
            const container = slide && slide.querySelector('.slide-container, .center-layout');
            if (!container) return;

            stabilizeSlideContainerShrinkOnly(container, { preserveEditedText: true });
            Reveal.layout();

            if (document.fonts && document.fonts.ready) {
                document.fonts.ready.then(() => {
                    stabilizeSlideContainerShrinkOnly(container, { preserveEditedText: true });
                    Reveal.layout();
                });
            }

            clearTimeout(container.themeStabilizeTimer);
            container.themeStabilizeTimer = setTimeout(() => {
                stabilizeSlideContainerShrinkOnly(container, { preserveEditedText: true });
                Reveal.layout();
            }, 520);
        }

        function setupImageLoadListeners() {
            document.querySelectorAll('.reveal img').forEach(img => {
                if (img.complete) return;

                img.addEventListener('load', () => {
                    const container = img.closest('.slide-container, .center-layout');
                    if (container) {
                        container.dataset.autofitDone = 'false';
                        autoFitContainer(container, { force: true, preserveEditedText: true });
                        Reveal.layout();
                    }
                });
            });
        }

        Reveal.on('ready', () => {
            const sections = document.querySelectorAll('.reveal .slides section');
            sections.forEach(section => {
                section.style.display = 'block';
                section.style.visibility = 'hidden';
            });

            setTimeout(() => {
                autoFitAllSlides();
                setupImageLoadListeners();
                if (typeof initLightbox === 'function') initLightbox();

                sections.forEach(section => {
                    section.style.display = '';
                    section.style.visibility = '';
                });

                if (typeof triggerGaugeAnimation === 'function') {
                    triggerGaugeAnimation(Reveal.getCurrentSlide());
                }
                Reveal.layout();
                stabilizeAfterPaint(null, 360);
            }, 150);
        });

        window.addEventListener('load', () => {
            setTimeout(() => {
                autoFitAllSlides({ preserveEditedText: true });
                Reveal.layout();
                stabilizeAfterPaint(null, 260);
            }, 50);
        });

        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(() => {
                autoFitAllSlides({ preserveEditedText: true });
                Reveal.layout();
                stabilizeAfterPaint(null, 260);
            });
        }

        Reveal.on('slidechanged', event => {
            const container = event.currentSlide && event.currentSlide.querySelector('.slide-container, .center-layout');
            if (container) stabilizeAfterPaint(container, 180);
            setTimeout(drawWorksheetMatchLines, 300);
        });

        document.addEventListener('input', event => {
            if (event.target.closest('[contenteditable="true"], .direct-editable')) {
                return;
            }
            const container = event.target.closest('.slide-container, .center-layout');
            if (container) {
                container.dataset.autofitDone = 'false';
                clearThemeAutofitBaseline(container);
                clearTimeout(container.autofitTimer);
                container.autofitTimer = setTimeout(() => {
                    autoFitContainer(container, { force: true, preserveEditedText: true });
                    Reveal.layout();
                }, 300);
            }
        });

        // 교사용 정답지 선 연결하기: 슬라이드와 완전히 동일한 방식으로 SVG 점→점 연결선 그리기
        // base.html의 getRelativePos + offsetLeft/Top 방식을 그대로 사용 (getBoundingClientRect 대신)
        function drawWorksheetMatchLines() {
            // 숨겨진 상태에서는 offsetLeft/Top이 0이므로 임시 표시
            const sections = document.querySelectorAll('.worksheet-section');
            const origStyles = [];
            sections.forEach(sec => {
                origStyles.push({ display: sec.style.display, visibility: sec.style.visibility, position: sec.style.position });
                sec.style.display = 'block';
                sec.style.visibility = 'hidden';
                sec.style.position = 'absolute';
            });

            // getRelativePos: base.html과 완전히 동일한 함수
            function getRelativePos(element, container) {
                let x = 0, y = 0;
                let el = element;
                while (el && el !== container && el !== document.body) {
                    x += el.offsetLeft;
                    y += el.offsetTop;
                    el = el.offsetParent;
                }
                return { x, y };
            }

            document.querySelectorAll('svg.match-answer-svg').forEach(svg => {
                const container = svg.closest('.matching-columns-container');
                if (!container) return;

                svg.querySelectorAll('g.ws-match-line').forEach(g => {
                    const startId = g.getAttribute('data-start');
                    const endId = g.getAttribute('data-end');
                    const startEl = document.querySelector(startId);
                    const endEl = document.querySelector(endId);
                    if (!startEl || !endEl) return;

                    const startPos = getRelativePos(startEl, container);
                    const endPos = getRelativePos(endEl, container);

                    // 점 중심 좌표 (슬라이드와 동일)
                    const startX = startPos.x + (startEl.offsetWidth / 2);
                    const startY = startPos.y + (startEl.offsetHeight / 2);
                    const endX = endPos.x + (endEl.offsetWidth / 2);
                    const endY = endPos.y + (endEl.offsetHeight / 2);

                    const path = g.querySelector('.match-svg-line');
                    const arrow = g.querySelector('.match-svg-arrowhead');

                    // 애니메이션 없이 즉시 완성형으로 그리기 (슬라이드는 requestAnimationFrame 사용)
                    if (path) {
                        path.setAttribute('d', `M${startX},${startY} L${endX},${endY}`);
                    }
                    if (arrow) {
                        const angle = Math.atan2(endY - startY, endX - startX) * (180 / Math.PI);
                        arrow.setAttribute('transform', `translate(${endX}, ${endY}) rotate(${angle})`);
                        arrow.setAttribute('points', '-16,-8 4,0 -16,8');
                    }
                });
            });

            // 원래 상태로 복구
            sections.forEach((sec, i) => {
                sec.style.display = origStyles[i].display;
                sec.style.visibility = origStyles[i].visibility;
                sec.style.position = origStyles[i].position;
            });
        }
        
        window.drawWorksheetMatchLines = drawWorksheetMatchLines;

        Reveal.on('ready', () => {
            setTimeout(drawWorksheetMatchLines, 500);
        });
        window.addEventListener('load', () => {
            setTimeout(drawWorksheetMatchLines, 300);
        });
