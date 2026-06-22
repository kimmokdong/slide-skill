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
        });

        function cssNumber(el, name, fallback) {
            const raw = getComputedStyle(el).getPropertyValue(name).trim();
            const parsed = parseFloat(raw);
            return Number.isFinite(parsed) ? parsed : fallback;
        }

        function hasLayoutBox(el) {
            const style = getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            if (el.clientWidth <= 0 || el.clientHeight <= 0) return false;
            return true;
        }

        function elementOverflows(el, boundaryRect) {
            if (!hasLayoutBox(el)) return false;
            const style = getComputedStyle(el);
            if (style.position === 'absolute' || style.position === 'fixed') return false;
            if (style.display === 'inline') return false;

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

        function restoreOriginalFontSize(el) {
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

        function autoFitContainer(container, options = {}) {
            if (container.dataset.autofitDone === 'true' && !options.force) return;
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
            const selector = [
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

            container.querySelectorAll(selector).forEach(el => {
                if (isTextSizeLocked(el)) return;
                restoreOriginalFontSize(el);
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

            stabilizeSlideContainer(container, { preserveEditedText: true });
            Reveal.layout();

            if (document.fonts && document.fonts.ready) {
                document.fonts.ready.then(() => {
                    stabilizeSlideContainer(container, { preserveEditedText: true });
                    Reveal.layout();
                });
            }

            clearTimeout(container.themeStabilizeTimer);
            container.themeStabilizeTimer = setTimeout(() => {
                stabilizeSlideContainer(container, { preserveEditedText: true });
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
                clearTimeout(container.autofitTimer);
                container.autofitTimer = setTimeout(() => {
                    autoFitContainer(container, { force: true, preserveEditedText: true });
                    Reveal.layout();
                }, 300);
            }
        });
