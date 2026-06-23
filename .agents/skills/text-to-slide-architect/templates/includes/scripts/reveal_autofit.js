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

        function elementOverflows(el, boundaryRect) {
            if (!hasLayoutBox(el)) return false;
            const style = getComputedStyle(el);
            if (style.position === 'absolute' || style.position === 'fixed') return false;

            const rect = el.getBoundingClientRect();
            const clipsX = style.overflowX !== 'visible';
            const clipsY = style.overflowY !== 'visible';
            const boxOverflow =
                (clipsY && el.scrollHeight > el.clientHeight + 2) ||
                (clipsX && el.scrollWidth > el.clientWidth + 2);
            const boundaryOverflow =
                rect.left < boundaryRect.left - 2 ||
                rect.top < boundaryRect.top - 2 ||
                rect.right > boundaryRect.right + 2 ||
                rect.bottom > boundaryRect.bottom + 2;

            return boxOverflow || boundaryOverflow;
        }

        const MAIN_AUTOFIT_SELECTOR = '.slide-header h2, .takeaway-content, .slide-body';
        const BAD_WRAP_SELECTOR = [
            '.stat-number',
            '.stat-label',
            '.bullet-text',
            '.comparison-card-title',
            '.matrix-label',
            '.roadmap-label',
            '.ox-text',
            '.timeline-date',
            '.timeline-title',
            '.summary-card-title',
            '.hands-on-steps li',
            '.tutorial-steps li',
            '.tutorial-tip .tip-text',
            '.tutorial-warning .tip-text'
        ].join(',');

        function bodyOverflows(body) {
            if (!body) return false;
            const boundaryRect = body.getBoundingClientRect();
            if (
                body.scrollHeight > body.clientHeight + 2 ||
                body.scrollWidth > body.clientWidth + 2
            ) {
                return true;
            }

            return Array.from(body.querySelectorAll('*'))
                .filter(hasLayoutBox)
                .some(child => elementOverflows(child, boundaryRect));
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
            return Array.from(new Set([
                ...container.querySelectorAll(MAIN_AUTOFIT_SELECTOR),
                ...container.querySelectorAll(BAD_WRAP_SELECTOR)
            ]));
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
                delete el.dataset.badWrapOriginalFontSize;
                delete el.dataset.badWrapOriginalFontPriority;
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

                if (el.classList.contains('slide-body')) {
                    if (Number.isFinite(size)) el.dataset.autofitSize = String(Math.round(size));
                }
            });
        }

        function restoreOriginalFontSize(el, options = {}) {
            if (options.useThemeBaseline && Object.prototype.hasOwnProperty.call(el.dataset, 'themeBaselineInlineFontSize')) {
                el.style.removeProperty('font-size');
                if (el.dataset.themeBaselineInlineFontSize) {
                    el.style.setProperty(
                        'font-size',
                        el.dataset.themeBaselineInlineFontSize,
                        el.dataset.themeBaselineInlineFontPriority || ''
                    );
                }
                return;
            }

            if (!Object.prototype.hasOwnProperty.call(el.dataset, 'badWrapOriginalFontSize')) {
                el.dataset.badWrapOriginalFontSize = el.style.getPropertyValue('font-size') || '';
                el.dataset.badWrapOriginalFontPriority = el.style.getPropertyPriority('font-size') || '';
            }

            el.style.removeProperty('font-size');
            if (el.dataset.badWrapOriginalFontSize) {
                el.style.setProperty(
                    'font-size',
                    el.dataset.badWrapOriginalFontSize,
                    el.dataset.badWrapOriginalFontPriority || ''
                );
            }
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

        function autoFitAllSlides(options = {}) {
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

        function shrinkBodyUntilFits(container) {
            const body = container.querySelector('.slide-body');
            if (!body) return;

            const computed = getComputedStyle(body);
            const minSize = Math.max(12, cssNumber(body, '--autofit-min', 18));
            let currentSize =
                parseFloat(body.style.fontSize) ||
                parseFloat(body.dataset.autofitSize) ||
                parseFloat(computed.fontSize) ||
                minSize;

            body.style.fontSize = currentSize + 'px';

            while (bodyOverflows(body) && currentSize > minSize) {
                currentSize -= 1;
                body.style.fontSize = currentSize + 'px';
            }

            body.dataset.autofitSize = String(Math.round(currentSize));
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

            const body = container.querySelector('.slide-body');
            if (body) {
                body.style.fontSize = '';
                const children = Array.from(body.querySelectorAll('*')).filter(hasLayoutBox);
                let minSize = Math.max(12, cssNumber(body, '--autofit-min', 18));
                let maxSize = Math.max(minSize, cssNumber(body, '--autofit-max', 56));
                let bestSize = minSize;

                while (minSize <= maxSize) {
                    const midSize = Math.floor((minSize + maxSize) / 2);
                    body.style.fontSize = midSize + 'px';

                    const boundaryRect = body.getBoundingClientRect();
                    let isOverflow =
                        body.scrollHeight > body.clientHeight + 2 ||
                        body.scrollWidth > body.clientWidth + 2;

                    if (!isOverflow) {
                        for (const child of children) {
                            if (elementOverflows(child, boundaryRect)) {
                                isOverflow = true;
                                break;
                            }
                        }
                    }

                    if (isOverflow) {
                        maxSize = midSize - 1;
                    } else {
                        bestSize = midSize;
                        minSize = midSize + 1;
                    }
                }

                body.style.fontSize = bestSize + 'px';
                body.dataset.autofitSize = String(bestSize);
            }

            fixBadVerticalWraps(container);
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

        function isBadVerticalWrap(el) {
            if (!hasLayoutBox(el) || isTextSizeLocked(el)) return false;
            const text = el.textContent.trim().replace(/\s+/g, '');
            if (text.length < 3) return false;

            const rect = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            const fontSize = parseFloat(style.fontSize) || 16;
            const lineHeight = parseFloat(style.lineHeight) || fontSize * 1.3;
            const lines = Math.max(1, Math.round(rect.height / lineHeight));
            const averageCharsPerLine = text.length / lines;
            const isCompactMetric = el.classList.contains('stat-number');

            return (
                (lines >= 3 && averageCharsPerLine <= 4.5 && rect.width < fontSize * 9) ||
                (isCompactMetric && lines >= 2 && text.length <= 6)
            );
        }

        function fixBadVerticalWraps(container) {
            const options = arguments[1] || {};
            container.querySelectorAll(BAD_WRAP_SELECTOR).forEach(el => {
                if (isTextSizeLocked(el)) return;
                restoreOriginalFontSize(el, options);
                el.style.wordBreak = 'keep-all';
                el.style.overflowWrap = 'normal';
                el.style.wordWrap = 'normal';

                const computed = getComputedStyle(el);
                let currentSize = parseFloat(computed.fontSize) || parseFloat(el.style.fontSize) || 16;
                const minSize = Math.max(12, cssNumber(el, '--bad-wrap-min', 15));

                while (isBadVerticalWrap(el) && currentSize > minSize) {
                    currentSize -= 1;
                    setAutofitFontSize(el, currentSize);
                }
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

                shrinkBodyUntilFits(container);
                fixBadVerticalWraps(container, { useThemeBaseline: true });
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

        function stabilizeAfterPaint(container, delay = 0) {
            const run = () => {
                if (container) {
                    stabilizeSlideContainer(container, { preserveEditedText: true });
                } else {
                    autoFitAllSlides({ preserveEditedText: true });
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
        });

        document.addEventListener('input', event => {
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
