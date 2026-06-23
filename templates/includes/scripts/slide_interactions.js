        function checkQuizAnswer(element, isCorrect) {
            if (element.classList.contains('quiz-correct') || element.classList.contains('quiz-wrong')) {
                return;
            }
            const parent = element.parentElement;
            if (parent && parent.querySelector('.quiz-correct')) {
                return; // 이미 정답을 맞췄으면 추가 선택 차단
            }

            if (isCorrect) {
                element.classList.add('quiz-correct');
            } else {
                element.classList.add('quiz-wrong');
            }
        }

        // 성과지표 가로형 게이지 바 애니메이션 구동 함수
        function triggerGaugeAnimation(slideElement) {
            if (!slideElement) return;

            // 다른 슬라이드 게이지 리셋
            document.querySelectorAll('.stat-gauge-bar').forEach(bar => {
                if (!slideElement.contains(bar)) {
                    bar.style.width = '0%';
                }
            });

            // 현재 슬라이드 게이지 활성화
            slideElement.querySelectorAll('.stat-gauge-bar').forEach(bar => {
                const targetWidth = bar.getAttribute('data-target-width') || '0%';
                setTimeout(() => {
                    bar.style.width = targetWidth;
                }, 100);
            });
        }

        // 성과지표 카드 클릭 시 게이지 채우기/비우기 토글 함수
        function clickStatCard(element, targetPercent) {
            const bar = element.querySelector('.stat-gauge-bar');
            if (!bar) return;
            
            // 현재 차있는 상태(targetPercent%)면 0%로 토글 리셋, 아니면 타겟으로 채움
            const currentWidth = bar.style.width;
            const targetWidthStr = targetPercent + '%';
            
            if (currentWidth === targetWidthStr) {
                bar.style.width = '0%';
            } else {
                bar.style.width = targetWidthStr;
            }
        }

        // Reveal.js 초기화
