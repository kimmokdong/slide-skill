        // ===== Review mode state and tools =====
        const REVIEW_STATE_STORAGE_KEY = `text-to-slide-review:${location.pathname}`;
        const reviewState = {
            global: "",
            local: {},
            order: [],
            textEdits: {},
            styleOverrides: {}
        };

        let currentSlideIndex = 0;
        let slideSorterInstance = null;
        let selectedEditable = null;
        let directEditBound = false;

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

        function isLocalDevServer() {
            return location.protocol === 'http:' && ['localhost', '127.0.0.1', '::1'].includes(location.hostname);
        }

        function loadReviewState() {
            try {
                const saved = JSON.parse(localStorage.getItem(REVIEW_STATE_STORAGE_KEY) || '{}');
                Object.assign(reviewState, {
                    global: saved.global || "",
                    local: saved.local || {},
                    order: Array.isArray(saved.order) ? saved.order : [],
                    textEdits: saved.textEdits || {},
                    styleOverrides: saved.styleOverrides || {}
                });
            } catch (err) {
                console.warn('Review state restore failed:', err);
            }
        }

        function persistReviewState() {
            try {
                localStorage.setItem(REVIEW_STATE_STORAGE_KEY, JSON.stringify(reviewState));
            } catch (err) {
                console.warn('Review state save failed:', err);
            }
        }

        loadReviewState();

        function scheduleReviewLayout() {
            if (typeof Reveal === 'undefined' || !Reveal.layout) return;
            requestAnimationFrame(() => Reveal.layout());
            setTimeout(() => Reveal.layout(), 80);
            setTimeout(() => Reveal.layout(), 430);
        }

        function toggleReviewMode() {
            document.body.classList.toggle('review-active');
            scheduleReviewLayout();

            if (document.body.classList.contains('review-active')) {
                initSlideSorter();
                updateCurrentSlideFeedbackView();
                updateSaveButtonAvailability();
                if (document.getElementById('pane-direct')?.classList.contains('active')) enableDirectEditing();
            } else {
                disableDirectEditing();
            }
        }

        document.addEventListener('keydown', (e) => {
            const tagName = e.target.tagName;
            if (e.key.toLowerCase() === 'e' && tagName !== 'TEXTAREA' && tagName !== 'INPUT' && !e.target.isContentEditable) {
                toggleReviewMode();
            }
        });

        Reveal.on('slidechanged', event => {
            currentSlideIndex = event.indexh;
            const container = event.currentSlide.querySelector('.slide-container, .center-layout');
            if (container && container.dataset.autofitDone !== "true") {
                autoFitContainer(container, { preserveEditedText: true });
            }
            triggerGaugeAnimation(event.currentSlide);
            if (document.body.classList.contains('review-active')) {
                updateCurrentSlideFeedbackView();
                if (document.getElementById('pane-direct')?.classList.contains('active')) refreshDirectEditingForCurrentSlide();
            }
            Reveal.layout();
        });

        function updateSaveButtonAvailability() {
            ['btn-save-layout', 'btn-save-theme', 'btn-save-text-edits'].forEach(id => {
                const btn = document.getElementById(id);
                if (!btn) return;
                btn.disabled = !isLocalDevServer();
                btn.title = isLocalDevServer() ? '' : '로컬 개발 서버(http://localhost)에서 열었을 때만 저장할 수 있습니다.';
            });
        }

        function updateCurrentSlideFeedbackView() {
            const label = document.getElementById('current-slide-label');
            const textarea = document.getElementById('local-feedback');
            if (!label || !textarea) return;
            label.textContent = `${currentSlideIndex + 1}번`;
            textarea.value = reviewState.local[currentSlideIndex] || "";
            textarea.oninput = (e) => {
                reviewState.local[currentSlideIndex] = e.target.value;
                persistReviewState();
            };
        }

        const globalFeedback = document.getElementById('global-feedback');
        if (globalFeedback) {
            globalFeedback.value = reviewState.global || "";
            globalFeedback.oninput = (e) => {
                reviewState.global = e.target.value;
                persistReviewState();
            };
        }

        function initSlideSorter() {
            const slides = Reveal.getSlides();
            const sorterList = document.getElementById('slide-sorter');
            if (!sorterList) return;

            const invalidOrder = reviewState.order.length !== slides.length ||
                reviewState.order.some(item => typeof item.originalIndex !== 'number' || item.originalIndex < 0 || item.originalIndex >= slides.length);

            if (invalidOrder) {
                reviewState.order = slides.map((slide, index) => {
                    const titleEl = slide.querySelector('h1, h2, h3');
                    const title = titleEl ? titleEl.innerText.trim() : `슬라이드 ${index + 1}`;
                    return { originalIndex: index, title, isDeleted: false };
                });
                persistReviewState();
            }

            renderSorterList();
            if (slideSorterInstance) slideSorterInstance.destroy();
            slideSorterInstance = null;
            if (window.Sortable) {
                slideSorterInstance = new Sortable(sorterList, {
                    animation: 150,
                    ghostClass: 'sortable-ghost',
                    onEnd: function (evt) {
                        const item = reviewState.order.splice(evt.oldIndex, 1)[0];
                        reviewState.order.splice(evt.newIndex, 0, item);
                        persistReviewState();
                        renderSorterList();
                    },
                });
            }
        }

        function renderSorterList() {
            const sorterList = document.getElementById('slide-sorter');
            if (!sorterList) return;
            sorterList.innerHTML = '';

            reviewState.order.forEach((item) => {
                const li = document.createElement('li');
                li.className = `slide-sorter-item ${item.isDeleted ? 'deleted' : ''}`;

                const num = document.createElement('div');
                num.className = 'slide-num';
                num.textContent = String(item.originalIndex + 1);

                const title = document.createElement('div');
                title.className = 'slide-title-preview';
                title.title = item.title || '';
                title.textContent = item.title || `슬라이드 ${item.originalIndex + 1}`;

                const action = document.createElement('button');
                action.className = `slide-action-btn ${item.isDeleted ? 'restore' : ''}`;
                action.type = 'button';
                action.textContent = item.isDeleted ? '복원' : '삭제';
                action.addEventListener('click', event => {
                    event.stopPropagation();
                    toggleDeleteSlide(item.originalIndex);
                });

                li.append(num, title, action);
                sorterList.appendChild(li);
            });
        }

        function toggleDeleteSlide(originalIndex) {
            const item = reviewState.order.find(i => i.originalIndex === originalIndex);
            if (item) {
                item.isDeleted = !item.isDeleted;
                persistReviewState();
                renderSorterList();
            }
        }

        function getThemePromptBlock() {
            if (typeof editorThemeSettings === 'undefined' || !editorThemeSettings) return "";
            const settings = typeof getThemeEditorPayload === 'function' ? getThemeEditorPayload() : null;
            if (!settings) return "";
            return "## 4. 슬라이드 동적 테마 요구사항\n" +
                "새로 생성하거나 수정할 슬라이드의 `meta.theme_colors`에 다음 설정을 반영해줘:\n\n" +
                "```json\n" + JSON.stringify({ theme_colors: settings }, null, 2) + "\n```\n\n";
        }

        function getDirectEditPromptBlock() {
            const keys = Object.keys(reviewState.textEdits || {});
            if (!keys.length && !Object.keys(reviewState.styleOverrides || {}).length) return "";
            let text = "## 5. 화면 직접 편집 반영사항\n";
            keys.forEach(key => {
                const edit = reviewState.textEdits[key];
                text += `- ${edit.slideIndex + 1}번 슬라이드 / ${edit.editId}: "${edit.value}"\n`;
            });
            Object.keys(reviewState.styleOverrides || {}).forEach(key => {
                const style = reviewState.styleOverrides[key];
                text += `- 글자 크기: ${key} -> ${style.fontSize}\n`;
            });
            return text + "\n";
        }

        function copyTextWithFallback(text) {
            if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
            return new Promise((resolve, reject) => {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.left = '-9999px';
                document.body.appendChild(textarea);
                textarea.focus();
                textarea.select();
                try {
                    document.execCommand('copy') ? resolve() : reject(new Error('execCommand copy failed'));
                } catch (err) {
                    reject(err);
                } finally {
                    textarea.remove();
                }
            });
        }

        function generateAndCopyPrompt() {
            let prompt = "# 슬라이드 일괄 수정 요청\n\n";

            if (reviewState.global.trim() !== "") {
                prompt += "## 1. 전체 수정 사항\n";
                prompt += reviewState.global.trim() + "\n\n";
            }

            let hasStructureChanges = false;
            let structureText = "## 2. 슬라이드 구성 변경\n";
            reviewState.order.forEach((item, newIndex) => {
                if (item.isDeleted) {
                    structureText += `- [삭제] 기존 ${item.originalIndex + 1}번 슬라이드 "${item.title}" 삭제\n`;
                    hasStructureChanges = true;
                } else if (item.originalIndex !== newIndex) {
                    structureText += `- [순서 변경] 기존 ${item.originalIndex + 1}번 슬라이드를 ${newIndex + 1}번째 위치로 이동\n`;
                    hasStructureChanges = true;
                }
            });
            if (hasStructureChanges) prompt += structureText + "\n";

            let hasLocalChanges = false;
            let localText = "## 3. 개별 슬라이드 수정\n";
            Object.keys(reviewState.local).forEach(slideIndexStr => {
                const sIdx = parseInt(slideIndexStr, 10);
                const feedback = (reviewState.local[sIdx] || '').trim();
                if (feedback) {
                    localText += `- [기존 ${sIdx + 1}번 슬라이드]: ${feedback}\n`;
                    hasLocalChanges = true;
                }
            });
            if (hasLocalChanges) prompt += localText + "\n";

            prompt += getThemePromptBlock();
            prompt += getDirectEditPromptBlock();

            if (prompt.trim() === "# 슬라이드 일괄 수정 요청") {
                alert("작성된 수정 요청 사항이 없습니다.");
                return;
            }

            copyTextWithFallback(prompt).then(() => {
                const btn = document.getElementById('btn-copy-prompt');
                const originalText = btn.innerHTML;
                btn.innerHTML = "복사 완료";
                btn.style.background = "#22c55e";
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.style.background = "";
                }, 2000);
            }).catch(err => {
                console.error("Clipboard copy failed:", err);
                alert("클립보드 복사에 실패했습니다. 브라우저 권한을 확인해주세요.");
            });
        }

        function validateActiveIndices(activeIndices) {
            const total = Reveal.getSlides().length;
            if (!activeIndices.length) return '최소 1장의 슬라이드는 남아 있어야 합니다.';
            const unique = new Set(activeIndices);
            if (unique.size !== activeIndices.length) return '중복된 슬라이드 인덱스가 있습니다.';
            if (activeIndices.some(idx => idx < 0 || idx >= total)) return '범위를 벗어난 슬라이드 인덱스가 있습니다.';
            return "";
        }

        function saveSlideLayoutToServer() {
            if (!isLocalDevServer()) {
                alert('로컬 개발 서버에서 열었을 때만 저장할 수 있습니다.');
                return;
            }
            const activeIndices = reviewState.order.filter(item => !item.isDeleted).map(item => item.originalIndex);
            const validationError = validateActiveIndices(activeIndices);
            if (validationError) {
                alert(validationError);
                return;
            }

            const btn = document.getElementById('btn-save-layout');
            const originalText = btn.innerHTML;
            btn.innerHTML = "저장 중...";
            btn.disabled = true;

            fetch('/api/save-order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ indices: activeIndices })
            })
            .then(response => {
                if (!response.ok) throw new Error("HTTP error " + response.status);
                return response.json();
            })
            .then(() => {
                btn.innerHTML = "저장 완료. 새로고침합니다.";
                btn.style.background = "#22c55e";
                localStorage.removeItem(REVIEW_STATE_STORAGE_KEY);
                setTimeout(() => window.location.reload(), 1000);
            })
            .catch(err => {
                btn.innerHTML = "저장 실패";
                btn.style.background = "#ef4444";
                btn.disabled = false;
                console.error("Layout save error:", err);
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.style.background = "";
                }, 2500);
            });
        }

        function getEditKey(slideIndex, editId) {
            return `${slideIndex}:${editId}`;
        }

        function getCurrentEditableElements() {
            const currentSlide = Reveal.getCurrentSlide();
            if (!currentSlide) return [];
            return [...currentSlide.querySelectorAll('[data-edit-id]')].filter(el => !el.closest('.review-sidebar'));
        }

        function enableDirectEditing() {
            bindDirectEditControls();
            refreshDirectEditingForCurrentSlide();
        }

        function disableDirectEditing() {
            document.querySelectorAll('.direct-editable, [contenteditable="true"]').forEach(el => {
                el.classList.remove('direct-editable', 'direct-edit-selected');
                el.removeAttribute('contenteditable');
            });
            selectedEditable = null;
            Reveal.configure({ keyboard: true });
        }

        function refreshDirectEditingForCurrentSlide() {
            getCurrentEditableElements().forEach(el => {
                el.classList.add('direct-editable');
                el.setAttribute('contenteditable', 'true');
                el.removeEventListener('focus', onDirectEditableFocus);
                el.removeEventListener('input', onDirectEditableInput);
                el.removeEventListener('blur', onDirectEditableBlur);
                el.addEventListener('focus', onDirectEditableFocus);
                el.addEventListener('input', onDirectEditableInput);
                el.addEventListener('blur', onDirectEditableBlur);
            });
        }

        function onDirectEditableFocus(event) {
            selectedEditable = event.currentTarget;
            document.querySelectorAll('.direct-edit-selected').forEach(el => el.classList.remove('direct-edit-selected'));
            selectedEditable.classList.add('direct-edit-selected');
            Reveal.configure({ keyboard: false });

            const selectedLabel = document.getElementById('direct-edit-selected');
            if (selectedLabel) selectedLabel.textContent = selectedEditable.dataset.editId;

            const px = parseInt(window.getComputedStyle(selectedEditable).fontSize, 10) || 32;
            syncFontControls(px);
        }

        function onDirectEditableInput(event) {
            const editId = event.currentTarget.dataset.editId;
            const key = getEditKey(currentSlideIndex, editId);
            reviewState.textEdits[key] = {
                slideIndex: currentSlideIndex,
                editId,
                value: event.currentTarget.innerText.trim()
            };
            persistReviewState();
        }

        function onDirectEditableBlur(event) {
            Reveal.configure({ keyboard: true });
            const container = event.currentTarget.closest('.slide-container, .center-layout');
            clearTimeout(container && container.directEditStabilizeTimer);
            if (container && typeof stabilizeSlideContainerShrinkOnly === 'function') {
                container.directEditStabilizeTimer = setTimeout(() => {
                    stabilizeSlideContainerShrinkOnly(container, { preserveEditedText: true });
                    Reveal.layout();
                }, 120);
            }
        }

        function syncFontControls(value) {
            const range = document.getElementById('direct-font-range');
            const number = document.getElementById('direct-font-number');
            const clamped = Math.max(12, Math.min(96, Number(value) || 32));
            if (range) range.value = clamped;
            if (number) number.value = clamped;
        }

        function applySelectedFontSize(value) {
            if (!selectedEditable) return;
            const clamped = Math.max(12, Math.min(96, Number(value) || 32));
            selectedEditable.style.setProperty('font-size', `${clamped}px`, 'important');
            selectedEditable.dataset.styleLocked = 'true';
            syncFontControls(clamped);

            const editId = selectedEditable.dataset.editId;
            const key = getEditKey(currentSlideIndex, editId);
            reviewState.styleOverrides[key] = {
                slideIndex: currentSlideIndex,
                editId,
                fontSize: `${clamped}px`
            };
            persistReviewState();
        }

        function bindDirectEditControls() {
            if (directEditBound) return;
            directEditBound = true;
            const range = document.getElementById('direct-font-range');
            const number = document.getElementById('direct-font-number');
            if (range) range.addEventListener('input', event => applySelectedFontSize(event.target.value));
            if (number) number.addEventListener('input', event => applySelectedFontSize(event.target.value));
        }

        function saveDirectTextEditsToServer() {
            if (!isLocalDevServer()) {
                alert('로컬 개발 서버에서 열었을 때만 저장할 수 있습니다.');
                return;
            }
            const btn = document.getElementById('btn-save-text-edits');
            const originalText = btn.innerHTML;
            btn.innerHTML = '저장 중...';
            btn.disabled = true;

            fetch('/api/save-text-edits', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    edits: Object.values(reviewState.textEdits || {}),
                    style_overrides: Object.values(reviewState.styleOverrides || {})
                })
            })
            .then(response => {
                if (!response.ok) throw new Error('HTTP error ' + response.status);
                return response.json();
            })
            .then(() => {
                btn.innerHTML = '저장 완료. 새로고침합니다.';
                btn.style.background = '#22c55e';
                localStorage.removeItem(REVIEW_STATE_STORAGE_KEY);
                setTimeout(() => window.location.reload(), 1000);
            })
            .catch(err => {
                console.error('Text edit save error:', err);
                btn.innerHTML = '저장 실패';
                btn.style.background = '#ef4444';
                btn.disabled = false;
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.style.background = '';
                }, 2500);
            });
        }

        updateSaveButtonAvailability();
