        // ===== 라이트박스 이미지 확대 기능 =====
        function initLightbox() {
            const images = document.querySelectorAll('.screenshot-img, .slide-body img, .slide-container img');
            images.forEach(img => {
                if (img.dataset.lightboxBound) return;
                img.dataset.lightboxBound = "true";

                img.addEventListener('click', (e) => {
                    // Reveal.js 슬라이드 전환 차단
                    e.stopPropagation();

                    const src = img.getAttribute('src');
                    const alt = img.getAttribute('alt') || img.getAttribute('title') || '이미지 확대 보기';

                    openLightbox(src, alt);
                });
            });
        }

        function openLightbox(src, captionText) {
            const lightbox = document.getElementById('image-lightbox');
            const targetImg = document.getElementById('lightbox-target-img');
            const caption = document.getElementById('lightbox-caption');

            targetImg.src = src;
            caption.textContent = captionText;
            lightbox.classList.add('active');

            // ESC 키 닫기 이벤트 등록
            document.addEventListener('keydown', handleLightboxEsc);
        }

        function closeLightbox() {
            const lightbox = document.getElementById('image-lightbox');
            lightbox.classList.remove('active');

            // ESC 키 닫기 이벤트 해제
            document.removeEventListener('keydown', handleLightboxEsc);
        }

        function handleLightboxEsc(e) {
            if (e.key === 'Escape') {
                closeLightbox();
            }
        }
