document.addEventListener('DOMContentLoaded', () => {
    const selectors = ['.review-toggle-fab', '.timer-toggle-fab', '.help-toggle-fab'];
    
    selectors.forEach(selector => {
        const fab = document.querySelector(selector);
        if (!fab) return;

        let isDragging = false;
        let startX, startY, initialX, initialY;
        let didMove = false;
        
        // 고유 저장 키 (예: fab-pos-.review-toggle-fab)
        const storageKey = 'fab-pos-' + selector;

        // 저장된 위치 불러오기
        const savedPos = localStorage.getItem(storageKey);
        if (savedPos) {
            try {
                const { x, y } = JSON.parse(savedPos);
                // 브라우저 크기가 바뀌었을 수도 있으므로 화면 안에 들어오도록 보정
                const safeX = Math.max(0, Math.min(x, window.innerWidth - 54));
                const safeY = Math.max(0, Math.min(y, window.innerHeight - 54));
                
                // right, bottom 기존 CSS 무시하고 left, top으로 고정
                fab.style.right = 'auto';
                fab.style.bottom = 'auto';
                fab.style.left = safeX + 'px';
                fab.style.top = safeY + 'px';
                fab.style.margin = '0';
            } catch(e) {}
        }

        const onDragStart = (e) => {
            // 버튼이 클릭된 상태(mousedown)를 저장
            isDragging = true;
            didMove = false;
            
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;

            startX = clientX;
            startY = clientY;

            const rect = fab.getBoundingClientRect();
            initialX = rect.left;
            initialY = rect.top;

            // right/top 기반 FAB를 left/top 좌표로 먼저 고정해야 첫 클릭 때 위치가 튀지 않는다.
            fab.style.left = initialX + 'px';
            fab.style.top = initialY + 'px';

            // 드래그 중에는 hover 트랜지션이나 크기 변화가 방해되지 않도록 설정
            fab.style.transition = 'none'; 
            fab.style.right = 'auto';
            fab.style.bottom = 'auto';
        };

        const onDragMove = (e) => {
            if (!isDragging) return;

            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;

            const dx = clientX - startX;
            const dy = clientY - startY;

            // 3px 이상 움직였으면 '드래그'로 판정하여 클릭 이벤트를 막음
            if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
                didMove = true;
                if (e.cancelable) e.preventDefault(); // 스크롤 등 방지
            }

            let newX = initialX + dx;
            let newY = initialY + dy;

            // 화면 밖으로 나가지 않도록 제한
            const maxX = window.innerWidth - fab.offsetWidth;
            const maxY = window.innerHeight - fab.offsetHeight;
            newX = Math.max(0, Math.min(newX, maxX));
            newY = Math.max(0, Math.min(newY, maxY));

            fab.style.left = newX + 'px';
            fab.style.top = newY + 'px';
        };

        const onDragEnd = (e) => {
            if (!isDragging) return;
            isDragging = false;
            fab.style.transition = ''; // 트랜지션 복구

            if (didMove) {
                // 최종 위치를 로컬 스토리지에 저장
                const rect = fab.getBoundingClientRect();
                localStorage.setItem(storageKey, JSON.stringify({
                    x: rect.left,
                    y: rect.top
                }));
            }
        };

        // 클릭 이벤트 가로채기 (드래그가 발생했다면 클릭 무시)
        fab.addEventListener('click', (e) => {
            if (didMove) {
                e.preventDefault();
                e.stopPropagation();
            }
        }, { capture: true });

        // 마우스 이벤트 연결
        fab.addEventListener('mousedown', onDragStart);
        document.addEventListener('mousemove', onDragMove);
        document.addEventListener('mouseup', onDragEnd);

        // 터치 이벤트 연결 (모바일/태블릿 지원)
        fab.addEventListener('touchstart', onDragStart, { passive: false });
        document.addEventListener('touchmove', onDragMove, { passive: false });
        document.addEventListener('touchend', onDragEnd);
    });
    
    // 창 크기 변경 시 화면 밖으로 나간 버튼들을 안으로 끌어오기
    window.addEventListener('resize', () => {
        selectors.forEach(selector => {
            const fab = document.querySelector(selector);
            if (!fab) return;
            const rect = fab.getBoundingClientRect();
            if (rect.right > window.innerWidth || rect.bottom > window.innerHeight) {
                const newX = Math.min(rect.left, window.innerWidth - fab.offsetWidth);
                const newY = Math.min(rect.top, window.innerHeight - fab.offsetHeight);
                fab.style.left = Math.max(0, newX) + 'px';
                fab.style.top = Math.max(0, newY) + 'px';
            }
        });
    });
});
