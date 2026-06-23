        // ===== 리뷰 모드 탭 전환 기능 =====
        function switchReviewTab(tabName) {
            document.querySelectorAll('.review-tab-btn').forEach(btn => btn.classList.remove('active'));
            const activeBtn = document.getElementById(`tab-btn-${tabName}`);
            if (activeBtn) activeBtn.classList.add('active');

            document.querySelectorAll('.review-tab-pane').forEach(pane => pane.classList.remove('active'));
            const activePane = document.getElementById(`pane-${tabName}`);
            if (activePane) activePane.classList.add('active');

            const btnCopy = document.getElementById('btn-copy-prompt');
            const btnApply = document.getElementById('btn-apply-theme');
            if (tabName === 'feedback') {
                btnCopy.style.display = 'flex';
                btnApply.style.display = 'none';
            } else {
                btnCopy.style.display = 'none';
                btnApply.style.display = 'flex';
            }
        }

        // ===== 테마 에디터 프리셋 설정 수동 매핑 =====
        function applyPresetToEditor(bg, bgSec, text, textSec, accent, accentSec, card, icon, font, pattern, decors, frame) {
            document.getElementById('editor-color-bg').value = bg;
            document.getElementById('editor-color-bg-secondary').value = bgSec;
            document.getElementById('editor-color-text').value = text;
            document.getElementById('editor-color-text-secondary').value = textSec;
            document.getElementById('editor-color-accent').value = accent;
            document.getElementById('editor-color-accent-secondary').value = accentSec;

            document.getElementById('editor-select-card').value = card;
            document.getElementById('editor-select-icon').value = icon;
            document.getElementById('editor-select-font').value = font;
            document.getElementById('editor-select-highlight').value = font;
            document.getElementById('editor-select-takeaway').value = font;
            document.getElementById('editor-select-motion').value = font;
            document.getElementById('editor-select-frame').value = frame;
            document.getElementById('editor-select-pattern').value = pattern;

            const decorsList = ['corner_accent', 'circles', 'hud_brackets', 'wavy_line', 'geometric_shapes', 'tech_grid_lines'];
            const checkboxIds = {
                'corner_accent': 'editor-check-decor-corner',
                'circles': 'editor-check-decor-circles',
                'hud_brackets': 'editor-check-decor-brackets',
                'wavy_line': 'editor-check-decor-wavy',
                'geometric_shapes': 'editor-check-decor-shapes',
                'tech_grid_lines': 'editor-check-decor-techlines'
            };

            decorsList.forEach(decor => {
                const cb = document.getElementById(checkboxIds[decor]);
                if (cb) cb.checked = decors.includes(decor);
            });
        }

        // ===== 테마 에디터 무작위 셔플 =====
        function applyRandomPresetToEditor() {
            const palettes = [
                { bg: '#fffbf0', bgSec: '#f4ebe1', text: '#1e293b', textSec: '#64748b', accent: '#ec4899', accentSec: '#818cf8' },
                { bg: '#0f172a', bgSec: '#1e293b', text: '#f8fafc', textSec: '#94a3b8', accent: '#6366f1', accentSec: '#a5b4fc' },
                { bg: '#ffffff', bgSec: '#f1f5f9', text: '#0f172a', textSec: '#475569', accent: '#2563eb', accentSec: '#1d4ed8' },
                { bg: '#fbf7f0', bgSec: '#ebd8c3', text: '#4a3319', textSec: '#7a5a3a', accent: '#d97706', accentSec: '#92400e' },
                { bg: '#fec2f2', bgSec: '#fee2e2', text: '#450a0a', textSec: '#7f1d1d', accent: '#ef4444', accentSec: '#b91c1c' },
                { bg: '#f2f4f2', bgSec: '#e2e8e2', text: '#1c2e1c', textSec: '#4a614a', accent: '#10b981', accentSec: '#6ee7b7' },
                { bg: '#18181b', bgSec: '#27272a', text: '#fafafa', textSec: '#a1a1aa', accent: '#f43f5e', accentSec: '#fda4af' },
                { bg: '#fff7ed', bgSec: '#ffedd5', text: '#431407', textSec: '#7c2d12', accent: '#ea580c', accentSec: '#fdba74' },
                // 9. 머스타드 옐로우 계열
                { bg: '#fefce8', bgSec: '#fef08a', text: '#422006', textSec: '#713f12', accent: '#eab308', accentSec: '#facc15' },
                // 10. 딥 퍼플 계열
                { bg: '#faf5ff', bgSec: '#f3e8ff', text: '#3b0764', textSec: '#581c87', accent: '#9333ea', accentSec: '#a855f7' },
                // 11. 포레스트 다크그린 계열 (자연 다크모드)
                { bg: '#052e16', bgSec: '#064e3b', text: '#ecfdf5', textSec: '#a7f3d0', accent: '#10b981', accentSec: '#34d399' }
            ];

            const cards = ['cute_note', 'tech_neon', 'business_clean', 'editorial_serif', 'retro_bold', 'transparent'];
            const icons = ['cute', 'tech', 'business', 'minimal_raw', 'handdrawn'];
            const fonts = ['friendly', 'cyber', 'classic', 'editorial', 'chalkboard'];
            const patterns = ['grid', 'dots', 'diagonal', 'blueprint', 'terrazzo', 'none'];
            const frames = ['cute', 'tech', 'business', 'retro', 'minimal'];
            const decorsList = ['corner_accent', 'circles', 'hud_brackets', 'wavy_line', 'geometric_shapes', 'tech_grid_lines'];

            const palette = palettes[Math.floor(Math.random() * palettes.length)];
            const card = cards[Math.floor(Math.random() * cards.length)];
            const icon = icons[Math.floor(Math.random() * icons.length)];
            const font = fonts[Math.floor(Math.random() * fonts.length)];
            const pattern = patterns[Math.floor(Math.random() * patterns.length)];
            const frame = frames[Math.floor(Math.random() * frames.length)];
            const chosenDecors = decorsList.filter(() => Math.random() < 0.4);

            applyPresetToEditor(
                palette.bg, palette.bgSec, palette.text, palette.textSec, palette.accent, palette.accentSec,
                card, icon, font, pattern, chosenDecors, frame
            );
        }

        // ===== 빔프로젝터 고대비 토글 기능 =====
        let isEditorContrast = false;
        function toggleEditorContrast() {
            isEditorContrast = !isEditorContrast;
            const reveal = document.querySelector('.reveal');
            const btn = document.getElementById('editor-btn-contrast');

            if (isEditorContrast) {
                reveal.classList.add('contrast-mode');
                btn.innerHTML = '<i class="fa-solid fa-circle-half-stroke"></i> 일반 테마 모드 복원';
                btn.style.background = '#10b981';
                btn.style.color = '#ffffff';
            } else {
                reveal.classList.remove('contrast-mode');
                btn.innerHTML = '<i class="fa-solid fa-circle-half-stroke"></i> 빔프로젝터 고대비 모드 ON';
                btn.style.background = '#fbbf24';
                btn.style.color = '#0f172a';
            }
        }

        // ===== 테마 실시간 적용 함수 (핵심 요구사항) =====
        let editorThemeSettings = null;

        function applyThemeEditorSettings() {
            const metaThemeStyle = document.getElementById('meta-theme-style');
            if (metaThemeStyle) {
                metaThemeStyle.disabled = true;
            }

            const bg = document.getElementById('editor-color-bg').value;
            const bgSec = document.getElementById('editor-color-bg-secondary').value;
            const text = document.getElementById('editor-color-text').value;
            const textSec = document.getElementById('editor-color-text-secondary').value;
            const accent = document.getElementById('editor-color-accent').value;
            const accentSec = document.getElementById('editor-color-accent-secondary').value;

            const card = document.getElementById('editor-select-card').value;
            const icon = document.getElementById('editor-select-icon').value;
            const font = document.getElementById('editor-select-font').value;
            const highlight = document.getElementById('editor-select-highlight').value;
            const takeaway = document.getElementById('editor-select-takeaway').value;
            const motion = document.getElementById('editor-select-motion').value;
            const frame = document.getElementById('editor-select-frame').value;
            const pattern = document.getElementById('editor-select-pattern').value;

            editorThemeSettings = { bg, bgSec, text, textSec, accent, accentSec, card, icon, font, highlight, takeaway, motion, frame, pattern, decors: [] };

            const root = document.documentElement;
            root.style.setProperty('--color-bg', bg);
            root.style.setProperty('--color-bg-secondary', bgSec);
            root.style.setProperty('--color-text', text);
            root.style.setProperty('--color-text-secondary', textSec);
            root.style.setProperty('--color-accent', accent);
            root.style.setProperty('--color-accent-secondary', accentSec);
            root.style.setProperty('--color-gradient', `linear-gradient(135deg, ${accent}, ${accentSec})`);

            const reveal = document.querySelector('.reveal');
            
            // 기존 프리셋 클래스 리셋 후 재등록
            reveal.className = 'reveal';
            if (isEditorContrast) reveal.classList.add('contrast-mode');

            reveal.classList.add(`card-preset-${card}`);
            reveal.classList.add(`icon-preset-${icon}`);
            reveal.classList.add(`theme-${font}`);
            reveal.classList.add(`highlight-${highlight}`);
            reveal.classList.add(`takeaway-${takeaway}`);
            reveal.classList.add(`motion-${motion}`);

            let fontStack = '';
            if (font === 'friendly') fontStack = "'Outfit', 'Noto Sans KR', sans-serif";
            else if (font === 'cyber') fontStack = "'Orbitron', 'Nanum Square Neo', sans-serif";
            else if (font === 'classic') fontStack = "'Playfair Display', 'Nanum Myeongjo', serif";
            else if (font === 'editorial') fontStack = "'Montserrat', 'Pretendard', sans-serif";
            else if (font === 'chalkboard') fontStack = "'Caveat', 'Nanum Pen Script', cursive";
            root.style.setProperty('--font-primary', fontStack);

            const frames = document.querySelectorAll('.screenshot-frame');
            frames.forEach(f => {
                const keepClasses = ['browser-frame', 'editable-image-frame', 'uploading']
                    .filter(cls => f.classList.contains(cls));
                f.className = 'screenshot-frame';
                keepClasses.forEach(cls => f.classList.add(cls));
                f.classList.add(`frame-${frame}`);
            });

            const patternOverlay = document.getElementById('patternOverlay');
            patternOverlay.className = 'pattern-overlay';
            if (pattern !== 'none') {
                patternOverlay.classList.add(`pattern-${pattern}`);
            }

            const checkboxIds = {
                'corner_accent': { id: 'editor-check-decor-corner', els: ['decorTL', 'decorTR', 'decorBL', 'decorBR'] },
                'circles': { id: 'editor-check-decor-circles', els: ['decorCircle1', 'decorCircle2'] },
                'hud_brackets': { id: 'editor-check-decor-brackets', els: ['decorHudL', 'decorHudR'] },
                'wavy_line': { id: 'editor-check-decor-wavy', els: ['decorWavy'] },
                'geometric_shapes': { id: 'editor-check-decor-shapes', els: ['decorShape1', 'decorShape2', 'decorShape3', 'decorShape4'] },
                'tech_grid_lines': { id: 'editor-check-decor-techlines', els: ['decorTechlines'] }
            };

            Object.keys(checkboxIds).forEach(decor => {
                const config = checkboxIds[decor];
                const cb = document.getElementById(config.id);
                const isChecked = cb ? cb.checked : false;
                if (isChecked) {
                    editorThemeSettings.decors.push(decor);
                }
                config.els.forEach(elId => {
                    const el = document.getElementById(elId);
                    if (el) el.classList.toggle('active', isChecked);
                });
            });

            Reveal.layout();
            autoFitAllSlides();

            // 비동기 폰트 다운로드 완료 시점 2차 재정합 (Layout Shift 방어)
            if (document.fonts && document.fonts.ready) {
                document.fonts.ready.then(() => {
                    console.log("[AutoFit] Fonts fully rendered after theme apply. Refitting...");
                    autoFitAllSlides();
                    Reveal.layout();
                });
            }

            const btnApply = document.getElementById('btn-apply-theme');
            const originalText = btnApply.innerHTML;
            btnApply.innerHTML = "✅ 테마 적용 완료!";
            btnApply.style.background = "#15a34a";
            setTimeout(() => {
                btnApply.innerHTML = originalText;
                btnApply.style.background = "";
            }, 1500);
        }

        // 퀴즈 정답/오답 확인 함수
