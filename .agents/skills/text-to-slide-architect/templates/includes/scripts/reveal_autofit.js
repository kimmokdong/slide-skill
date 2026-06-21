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

        function autoFitAllSlides() {
            document.querySelectorAll('.slide-container, .center-layout').forEach(container => {
                autoFitContainer(container, { force: true });
            });
        }

        function fitSingleLine(el, maxVar, minVar, maxFallback, minFallback) {
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

            container.dataset.autofitDone = 'true';
        }

        function setupImageLoadListeners() {
            document.querySelectorAll('.reveal img').forEach(img => {
                if (img.complete) return;

                img.addEventListener('load', () => {
                    const container = img.closest('.slide-container, .center-layout');
                    if (container) {
                        container.dataset.autofitDone = 'false';
                        autoFitContainer(container, { force: true });
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
            }, 150);
        });

        window.addEventListener('load', () => {
            setTimeout(() => {
                autoFitAllSlides();
                Reveal.layout();
            }, 50);
        });

        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(() => {
                autoFitAllSlides();
                Reveal.layout();
            });
        }

        document.addEventListener('input', event => {
            const container = event.target.closest('.slide-container, .center-layout');
            if (container) {
                container.dataset.autofitDone = 'false';
                clearTimeout(container.autofitTimer);
                container.autofitTimer = setTimeout(() => {
                    autoFitContainer(container, { force: true });
                    Reveal.layout();
                }, 300);
            }
        });
