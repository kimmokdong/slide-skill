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

        // ===== PowerPoint식 텍스트 자동 맞춤 (Auto-Fit) =====
        function autoFitAllSlides() {
            // slide-container 단위로 폰트 스케일링 체크
            document.querySelectorAll('.slide-container, .center-layout').forEach(container => {
                autoFitContainer(container);
            });
        }

        function autoFitContainer(container) {
            if (container.dataset.autofitDone === "true") return;

            // 제목 구역은 높이/위치를 고정하고, 가로로 넘칠 때만 h2 글자를 줄입니다.
            function fitTitleInHeader(header) {
                const h2 = header.querySelector('h2');
                if (!h2) return;

                h2.style.whiteSpace = 'nowrap';
                let headerSize = parseFloat(getComputedStyle(h2).fontSize) || 48;
                const minHeaderSize = header.classList.contains('tutorial-title-box') ? 28 : 32;

                for (let i = 0; i < 45 && headerSize > minHeaderSize; i++) {
                    const tooWide = h2.scrollWidth > h2.clientWidth + 2;
                    if (!tooWide) break;
                    headerSize -= 1.0;
                    h2.style.fontSize = headerSize + 'px';
                }
            }

            container.querySelectorAll('.slide-header').forEach(fitTitleInHeader);

            // 폰트 초기화 (CSS 기본값으로 복원)
            container.style.fontSize = '';

            // O/X 표는 좌우 컬럼 폭을 먼저 고정하고, 각 컬럼 내부 글자만 폭에 맞춰 줄입니다.
            function fitNowrapElements(selector, minPx) {
                container.querySelectorAll(selector).forEach(el => {
                    let size = parseFloat(getComputedStyle(el).fontSize);
                    if (!size) return;
                    for (let i = 0; i < 60 && size > minPx; i++) {
                        if (el.scrollWidth <= el.clientWidth + 1) break;
                        size -= 1;
                        el.style.fontSize = size + 'px';
                    }
                });
            }

            function overflowsHorizontally(el) {
                if (!el || el.clientWidth <= 0) return false;
                if (el.scrollWidth > el.clientWidth + 1) return true;
                const parentRect = el.getBoundingClientRect();
                for (let child of el.children) {
                    const rect = child.getBoundingClientRect();
                    if (rect.left < parentRect.left - 1 || rect.right > parentRect.right + 1) {
                        return true;
                    }
                    if (child.scrollWidth > child.clientWidth + 1) {
                        return true;
                    }
                }
                return false;
            }

            function clipsOwnContent(el) {
                if (!el || el.clientWidth <= 0 || el.clientHeight <= 0) return false;
                return el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1;
            }

            function oxItemClips(item) {
                const text = item.querySelector('.ox-text');
                return overflowsHorizontally(item) || clipsOwnContent(item) || clipsOwnContent(text);
            }

            function fitOxContent() {
                container.querySelectorAll('.ox-column-header').forEach(header => {
                    let size = parseFloat(getComputedStyle(header).fontSize);
                    if (!size) return;
                    for (let i = 0; i < 80 && size > 28; i++) {
                        const title = header.querySelector('h3');
                        if (!overflowsHorizontally(header) && !clipsOwnContent(title)) break;
                        size -= 1;
                        header.style.fontSize = size + 'px';
                    }
                });

                container.querySelectorAll('.ox-item').forEach(item => {
                    let size = parseFloat(getComputedStyle(item).fontSize);
                    if (!size) return;
                    for (let i = 0; i < 90 && size > 22; i++) {
                        if (!oxItemClips(item)) break;
                        size -= 1;
                        item.style.fontSize = size + 'px';
                    }
                });

                container.querySelectorAll('.ox-column-body').forEach(body => {
                    const items = Array.from(body.querySelectorAll('.ox-item'));
                    if (!items.length) return;
                    let size = Math.min(...items.map(item => parseFloat(getComputedStyle(item).fontSize)).filter(Boolean));
                    if (!size) return;
                    for (let i = 0; i < 120 && size > 18; i++) {
                        const bodyClips = clipsOwnContent(body);
                        const itemClips = items.some(item => oxItemClips(item));
                        if (!bodyClips && !itemClips) break;
                        size -= 1;
                        items.forEach(item => item.style.fontSize = size + 'px');
                    }
                });
            }

            fitOxContent();

            let currentSize = parseFloat(getComputedStyle(container).fontSize);
            const minSize = 11; // 원본의 약 50% 수준 이하로 축소 허용 (기존 13)
            const maxIterations = 60; // 반복 한계치 확장 (기존 35)

            const body = container.querySelector('.slide-body');

            // 컨테이너나 내부 슬라이드 바디 영역이 한도를 넘어서면 넘침으로 판정
            function hasOverflow() {
                // 1. 기하학적 겹침 감지 (마지막 핵심 콘텐츠 요소와 하단 요약 바의 경계 체크)
                const takeawayBar = container.querySelector('.bottom-takeaway-bar');
                if (takeawayBar) {
                    const takeawayRect = takeawayBar.getBoundingClientRect();
                    // 하단 바보다 위에 있어야 하는 콘텐츠 요소들을 조사
                    const contentElements = container.querySelectorAll('.slide-body, .tutorial-tip, .tutorial-warning, .bullet-list, .hands-on-steps, .ox-layout');
                    for (let el of contentElements) {
                        const elRect = el.getBoundingClientRect();
                        // 콘텐츠 요소의 바텀이 하단 바의 탑보다 아래로 넘어가면 오버플로우로 판정
                        if (elRect.bottom > takeawayRect.top + 2) {
                            console.log("[AutoFit Debug] Geometrical overflow with takeaway bar detected:", el, "bottom:", elRect.bottom, "bar top:", takeawayRect.top);
                            return true;
                        }
                    }
                }

                // 2. 전체 컨테이너 높이 대비 경계 체크 (기하학적 캔버스 바텀 영역 체크)
                const containerRect = container.getBoundingClientRect();
                const allElements = container.querySelectorAll('*');
                for (let el of allElements) {
                    const style = getComputedStyle(el);
                    if (el.closest('.slide-header')) {
                        continue;
                    }
                    const clipper = el.closest('.slide-body, .split-layout .left, .tutorial-text, .ox-column-body, .roadmap-step');
                    if (clipper && clipper !== el) {
                        const clippedRect = el.getBoundingClientRect();
                        const clipRect = clipper.getBoundingClientRect();
                        if (clippedRect.bottom > clipRect.bottom + 2 || clippedRect.top < clipRect.top - 2) {
                            console.log("[AutoFit Debug] Clipped by parent:", el, "clipper:", clipper);
                            return true;
                        }
                    }
                    if (style.position === 'absolute' || el.clientHeight === 0) {
                        continue;
                    }
                    const elRect = el.getBoundingClientRect();
                    // 요소의 바텀이 컨테이너의 바텀보다 아래로 내려갔는지 체크 (패딩 영역 감안하여 12px 버퍼)
                    if (elRect.bottom > containerRect.bottom - 12) {
                        // 하단 요약 바 자체는 컨테이너 안에 깔리므로 예외 처리
                        if (el.classList.contains('bottom-takeaway-bar') || el.closest('.bottom-takeaway-bar')) {
                            continue;
                        }
                        console.log("[AutoFit Debug] Geometrical container overflow detected:", el, "bottom:", elRect.bottom, "container bottom:", containerRect.bottom);
                        return true;
                    }
                }

                // 3. 본문 영역 scrollHeight 방식 백업 적용 (제목 영역은 제외)
                if (body && body.scrollHeight > body.clientHeight + 4) {
                    return true;
                }
                for (let el of allElements) {
                    const style = getComputedStyle(el);
                    if (el.closest('.slide-header')) {
                        continue;
                    }
                    if (style.position === 'absolute') {
                        continue;
                    }
                    if (el.clientHeight > 0 && el.scrollHeight > el.clientHeight + 2) {
                        return true;
                    }
                    if (style.whiteSpace === 'nowrap' && el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 2) {
                        return true;
                    }
                }
                return false;
            }

            let iterations = 0;
            while (hasOverflow() && currentSize > minSize && iterations < maxIterations) {
                currentSize -= 0.5; // 정밀하게 0.5px 단위로 줄임
                container.style.fontSize = currentSize + 'px';
                iterations++;
            }
            container.dataset.autofitDone = "true";
        }

        // 모든 이미지에 onload 이벤트 리스너를 달아, 이미지가 늦게 다운로드 로드되더라도 완료 시점에 autoFitContainer를 재정합합니다.
        function setupImageLoadListeners() {
            document.querySelectorAll('.reveal img').forEach(img => {
                // 이미 로딩이 완료된 경우
                if (img.complete) {
                    return;
                }
                
                // 로딩이 진행 중인 경우 onload 리스너 등록
                img.addEventListener('load', () => {
                    console.log("[AutoFit] Image load completed, refitting slide container:", img.src);
                    const container = img.closest('.slide-container, .center-layout');
                    if (container) {
                        autoFitContainer(container);
                        Reveal.layout();
                    }
                });
            });
        }

        // Reveal.js 준비 완료 후 자동 실행
        Reveal.on('ready', () => {
            // 레이아웃 높이 계산을 위해 비활성 슬라이드도 잠시 강제 노출
            const sections = document.querySelectorAll('.reveal .slides section');
            sections.forEach(s => {
                s.style.display = 'block';
                s.style.visibility = 'hidden';
            });

            setTimeout(() => {
                autoFitAllSlides();
                setupImageLoadListeners(); // 이미지 onload 리스너 세팅
                initLightbox(); // 라이트박스 초기화

                // 원래 상태로 복구
                sections.forEach(s => {
                    s.style.display = '';
                    s.style.visibility = '';
                });
                triggerGaugeAnimation(Reveal.getCurrentSlide()); // 첫 슬라이드 게이지바 구동
                Reveal.layout();
            }, 150);
        });

        // 리소스가 완전히 다운로드 완료된 window load 시점에 최종 확인 사격
        window.addEventListener('load', () => {
            setTimeout(() => {
                console.log("[AutoFit] Window onload triggered, performing final fit synchronization");
                autoFitAllSlides();
                Reveal.layout();
            }, 50);
        });

        // 웹 폰트(Noto Sans KR 등) 로딩 완료 시점에 폰트 축소 강제 재정합
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(() => {
                console.log("[AutoFit] Fonts loaded, refitting slides");
                autoFitAllSlides();
                Reveal.layout();
            });
        }
