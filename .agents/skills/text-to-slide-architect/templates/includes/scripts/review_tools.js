        // ===== 리뷰 모드 관련 로직 (Review Mode Logic) =====
        const reviewState = {
            global: "",
            local: {},
            order: [],
        };

        let currentSlideIndex = 0;
        const MAX_UPLOAD_IMAGE_BYTES = 15 * 1024 * 1024;

        document.addEventListener('click', (event) => {
            const frame = event.target.closest ? event.target.closest('.editable-image-frame') : null;
            if (!frame || !document.body.classList.contains('review-active')) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            triggerImageUpload(frame);
        }, true);

        function triggerImageUpload(element) {
            if (!element || element.dataset.uploading === "true") {
                return;
            }

            const slideIndex = Number.parseInt(element.dataset.slideIndex, 10);
            const targetKey = element.dataset.targetKey;
            if (!Number.isInteger(slideIndex) || !targetKey) {
                alert("이미지 위치 정보를 찾을 수 없습니다. HTML을 다시 빌드한 뒤 시도해 주세요.");
                return;
            }

            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/png,image/jpeg,image/gif,image/webp';
            input.style.display = 'none';

            input.addEventListener('change', () => {
                const file = input.files && input.files[0];
                input.remove();
                if (!file) return;

                uploadEditableImage(element, slideIndex, targetKey, file);
            }, { once: true });

            document.body.appendChild(input);
            input.click();
        }

        function readImageAsDataUrl(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = () => reject(reader.error || new Error("이미지를 읽지 못했습니다."));
                reader.readAsDataURL(file);
            });
        }

        async function uploadEditableImage(element, slideIndex, targetKey, file) {
            if (file.size > MAX_UPLOAD_IMAGE_BYTES) {
                alert("이미지 파일은 15MB 이하만 업로드할 수 있습니다.");
                return;
            }

            element.dataset.uploading = "true";
            element.classList.add('uploading');

            try {
                const imageData = await readImageAsDataUrl(file);
                const response = await fetch('/api/upload-image', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        slide_index: slideIndex,
                        target_key: targetKey,
                        filename: file.name,
                        file_type: file.type,
                        image_data: imageData,
                    }),
                });

                const rawText = await response.text();
                let data = {};
                try {
                    data = rawText ? JSON.parse(rawText) : {};
                } catch (_err) {
                    data = {};
                }

                if (!response.ok) {
                    throw new Error(data.message || rawText || `HTTP error ${response.status}`);
                }

                window.location.reload();
            } catch (err) {
                alert(`이미지 업로드에 실패했습니다.\n${err.message || err}`);
                console.error("Image upload error:", err);
                element.dataset.uploading = "false";
                element.classList.remove('uploading');
            }
        }

        function toggleReviewMode() {
            document.body.classList.toggle('review-active');
            setTimeout(() => {
                Reveal.layout(); // 스크롤 레이아웃 갱신
            }, 400);

            if (document.body.classList.contains('review-active')) {
                initSlideSorter();
                updateCurrentSlideFeedbackView();
            }
        }

        // 'E' 키 토글
        document.addEventListener('keydown', (e) => {
            if (e.key.toLowerCase() === 'e' && e.target.tagName !== 'TEXTAREA' && e.target.tagName !== 'INPUT') {
                toggleReviewMode();
            }
        });

        Reveal.on('slidechanged', event => {
            currentSlideIndex = event.indexh;
            // 활성화된 슬라이드에만 폰트 피팅 적용 (display:none 상태 회피)
            const container = event.currentSlide.querySelector('.slide-container, .center-layout');
            if (container && container.dataset.autofitDone !== "true") {
                autoFitContainer(container);
            }
            triggerGaugeAnimation(event.currentSlide); // 슬라이드 전환 시 게이지바 애니메이션 구동
            if (document.body.classList.contains('review-active')) {
                updateCurrentSlideFeedbackView();
            }
            Reveal.layout();
        });

        function updateCurrentSlideFeedbackView() {
            const label = document.getElementById('current-slide-label');
            const textarea = document.getElementById('local-feedback');

            label.textContent = `${currentSlideIndex + 1}번`;
            textarea.value = reviewState.local[currentSlideIndex] || "";

            textarea.oninput = (e) => {
                reviewState.local[currentSlideIndex] = e.target.value;
            };
        }

        document.getElementById('global-feedback').oninput = (e) => {
            reviewState.global = e.target.value;
        };

        function initSlideSorter() {
            const slides = Reveal.getSlides();
            const sorterList = document.getElementById('slide-sorter');

            if (reviewState.order.length === 0 || reviewState.order.length !== slides.length) {
                reviewState.order = slides.map((slide, index) => {
                    const titleEl = slide.querySelector('h1, h2, h3');
                    const title = titleEl ? titleEl.innerText : `슬라이드 ${index + 1}`;
                    return { originalIndex: index, title: title, isDeleted: false };
                });
            }

            renderSorterList();

            new Sortable(sorterList, {
                animation: 150,
                ghostClass: 'sortable-ghost',
                onEnd: function (evt) {
                    const item = reviewState.order.splice(evt.oldIndex, 1)[0];
                    reviewState.order.splice(evt.newIndex, 0, item);
                },
            });
        }

        function renderSorterList() {
            const sorterList = document.getElementById('slide-sorter');
            sorterList.innerHTML = '';

            reviewState.order.forEach((item, currentIndex) => {
                const li = document.createElement('li');
                li.className = `slide-sorter-item ${item.isDeleted ? 'deleted' : ''}`;

                li.innerHTML = `
                    <div class="slide-num">${item.originalIndex + 1}</div>
                    <div class="slide-title-preview" title="${item.title}">${item.title}</div>
                    <button class="slide-action-btn ${item.isDeleted ? 'restore' : ''}" onclick="event.stopPropagation(); toggleDeleteSlide(${item.originalIndex})">
                        ${item.isDeleted ? '↩️' : '❌'}
                    </button>
                `;
                sorterList.appendChild(li);
            });
        }

        function toggleDeleteSlide(originalIndex) {
            const item = reviewState.order.find(i => i.originalIndex === originalIndex);
            if (item) {
                item.isDeleted = !item.isDeleted;
                renderSorterList();
            }
        }

        function generateAndCopyPrompt() {
            let prompt = "# 🛠️ 슬라이드 일괄 수정 요청서\n\n";

            if (reviewState.global.trim() !== "") {
                prompt += "## 1. 전체 수정 사항 (Global)\n";
                prompt += reviewState.global.trim() + "\n\n";
            }

            let hasStructureChanges = false;
            let structureText = "## 2. 슬라이드 구조 변경 (Structure)\n";

            reviewState.order.forEach((item, newIndex) => {
                if (item.isDeleted) {
                    structureText += `- [삭제] 기존 ${item.originalIndex + 1}번 슬라이드 ("${item.title}") 삭제\n`;
                    hasStructureChanges = true;
                } else if (item.originalIndex !== newIndex) {
                    structureText += `- [순서 변경] 기존 ${item.originalIndex + 1}번 슬라이드를 ${newIndex + 1}번째 위치로 이동\n`;
                    hasStructureChanges = true;
                }
            });

            if (hasStructureChanges) {
                prompt += structureText + "\n";
            }

            let hasLocalChanges = false;
            let localText = "## 3. 개별 슬라이드 수정 (Local)\n";

            Object.keys(reviewState.local).forEach(slideIndexStr => {
                const sIdx = parseInt(slideIndexStr);
                const feedback = reviewState.local[sIdx].trim();
                if (feedback) {
                    localText += `- **[기존 ${sIdx + 1}번 슬라이드]**: ${feedback}\n`;
                    hasLocalChanges = true;
                }
            });

            if (hasLocalChanges) {
                prompt += localText + "\n";
            }

            let hasThemeChanges = false;
            if (editorThemeSettings) {
                prompt += "## 4. 슬라이드 동적 테마 요구사항 (Theme Colors & Presets)\n";
                prompt += "새로 생성할 슬라이드의 `meta.theme_colors` 영역에 다음 테마 설정과 60-30-10 규칙을 그대로 기재해줘:\n\n";
                
                const themeColorsJson = {
                    "bg": editorThemeSettings.bg,
                    "bg_secondary": editorThemeSettings.bgSec,
                    "text": editorThemeSettings.text,
                    "text_secondary": editorThemeSettings.textSec,
                    "accent": editorThemeSettings.accent,
                    "accent_secondary": editorThemeSettings.accentSec,
                    "card_style_preset": editorThemeSettings.card,
                    "icon_preset": editorThemeSettings.icon,
                    "font_preset": editorThemeSettings.font,
                    "highlight_style": editorThemeSettings.highlight,
                    "takeaway_style": editorThemeSettings.takeaway,
                    "motion_preset": editorThemeSettings.motion,
                    "image_frame_preset": editorThemeSettings.frame,
                    "bg_pattern_style": editorThemeSettings.pattern,
                    "decorations": editorThemeSettings.decors
                };
                
                prompt += "```json\n" + JSON.stringify({ "theme_colors": themeColorsJson }, null, 2) + "\n```\n";
                hasThemeChanges = true;
            }

            if (!hasStructureChanges && !hasLocalChanges && !hasThemeChanges && reviewState.global.trim() === "") {
                alert("작성된 수정 요청 사항이 없습니다.");
                return;
            }

            navigator.clipboard.writeText(prompt).then(() => {
                const btn = document.getElementById('btn-copy-prompt');
                const originalText = btn.innerHTML;
                btn.innerHTML = "✅ 복사 완료! 채팅창에 붙여넣으세요";
                btn.style.background = "#22c55e";
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.style.background = "";
                }, 3000);
            }).catch(err => {
                alert("클립보드 복사에 실패했습니다. 콘솔을 확인해주세요.");
                console.error("Clipboard copy failed:", err);
            });
        }

        function saveSlideLayoutToServer() {
            // 삭제되지 않은(isDeleted: false) 슬라이드들만 필터링하여 원래 인덱스의 배열을 생성
            const activeIndices = reviewState.order
                .filter(item => !item.isDeleted)
                .map(item => item.originalIndex);

            const btn = document.getElementById('btn-save-layout');
            const originalText = btn.innerHTML;
            btn.innerHTML = "💾 저장 중...";
            btn.disabled = true;

            // 로컬 개발 서버로 POST 요청 전송
            fetch('/api/save-order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    indices: activeIndices
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error("HTTP error " + response.status);
                }
                return response.json();
            })
            .then(data => {
                btn.innerHTML = "✅ 저장 완료! 새로고침합니다...";
                btn.style.background = "#22c55e";
                setTimeout(() => {
                    window.location.reload();
                }, 1200);
            })
            .catch(err => {
                btn.innerHTML = "❌ 저장 실패! (서버 오프라인)";
                btn.style.background = "#ef4444";
                btn.disabled = false;
                console.error("Layout save error:", err);
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.style.background = "";
                }, 3000);
            });
        }
