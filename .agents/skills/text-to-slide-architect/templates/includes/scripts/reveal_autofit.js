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

            // 1. 제목 영역 (가로로 넘칠 때만 줄임)
            container.querySelectorAll('.slide-header h2').forEach(h2 => {
                h2.style.whiteSpace = 'nowrap';
                h2.style.fontSize = '80px';
                while (h2.scrollWidth > h2.clientWidth + 2 && parseFloat(h2.style.fontSize) > 28) {
                    h2.style.fontSize = (parseFloat(h2.style.fontSize) - 1) + 'px';
                }
            });

            // 2. 하단바 영역 (상자 크기 안에서 최대한 크게)
            container.querySelectorAll('.takeaway-content').forEach(tc => {
                tc.style.fontSize = '60px'; // 넉넉하게 시작
                while ((tc.scrollHeight > tc.clientHeight + 2 || tc.scrollWidth > tc.clientWidth + 2) && parseFloat(tc.style.fontSize) > 20) {
                    tc.style.fontSize = (parseFloat(tc.style.fontSize) - 1) + 'px';
                }
            });

            // 3. 본문 영역 (.slide-body) - 유니버설 분산형 오토핏
            // 기하학적 겹침 꼼수는 버리되, 자식 요소 내부의 오버플로우 은닉(Swallowed Overflow)을 감지하는 센서는 복구
            const body = container.querySelector('.slide-body');
            
            if (body) {
                // 브라우저의 DOM/CSS 엔진 렌더링 스펙에 따른 근본적인 센서 필터링
                const children = Array.from(body.querySelectorAll('*')).filter(el => {
                    const style = getComputedStyle(el);
                    
                    // 1. 화면에 렌더링되지 않거나, 브라우저가 공간을 0으로 할당한 요소 배제 (숨김 처리 등)
                    if (el.clientWidth === 0 || el.clientHeight === 0) return false;
                    
                    // 2. 인라인 요소 배제 (중요!)
                    // 브라우저는 순수 inline 요소(span, strong 등)의 clientWidth를 0으로 계산하는 경우가 많으며,
                    // 이때 scrollWidth는 텍스트 길이로 반환되므로 'scrollWidth > clientWidth'가 무조건 true가 되는 치명적 오탐지 발생
                    if (style.display === 'inline') return false;
                    
                    // 3. 레이아웃 흐름에서 벗어난 절대 좌표 요소 배제
                    if (style.position === 'absolute' || style.position === 'fixed') return false;
                    
                    // 위 조건을 통과한 모든 요소(Block, Flex, Grid 박스)는 검사 대상!
                    // 예: .split-layout .left, .ox-column 등 높이가 제한되어 오버플로우가 발생할 수 있는 모든 상자
                    return true;
                });

                // 브라우저의 레이아웃 엔진(scrollHeight)만 믿고 이분 탐색(Binary Search) 수행
                let minSize = 16;
                let maxSize = 100;
                let bestSize = minSize;

                while (minSize <= maxSize) {
                    let midSize = Math.floor((minSize + maxSize) / 2);
                    body.style.fontSize = midSize + 'px';
                    
                    // 1차: 본문 전체가 터졌는가?
                    let isOverflow = (body.scrollHeight > body.clientHeight + 2) || (body.scrollWidth > body.clientWidth + 2);

                    // 2차: 내부 박스(ox-column 등)가 글씨를 숨겨서 잘라먹었는가?
                    if (!isOverflow) {
                        for (let child of children) {
                            if (child.scrollHeight > child.clientHeight + 2 || child.scrollWidth > child.clientWidth + 2) {
                                isOverflow = true;
                                break;
                            }
                        }
                    }

                    if (isOverflow) {
                        // 넘치면 크기를 줄여야 함
                        maxSize = midSize - 1;
                    } else {
                        // 안 넘치면 일단 합격! 최적값으로 저장하고, "혹시 더 키울 수 있을까?" 하고 큰 쪽을 다시 탐색
                        bestSize = midSize;
                        minSize = midSize + 1;
                    }
                }
                
                // 최종 적용
                body.style.fontSize = bestSize + 'px';
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

        // 에디터 모드 대응: 사용자가 텍스트 편집 시 실시간으로 다시 핏팅 수행
        document.addEventListener('input', (e) => {
            const container = e.target.closest('.slide-container, .center-layout');
            if (container) {
                container.dataset.autofitDone = "false";
                clearTimeout(container.autofitTimer);
                container.autofitTimer = setTimeout(() => {
                    autoFitContainer(container);
                    Reveal.layout();
                }, 300); // 300ms 디바운싱 처리
            }
        });
