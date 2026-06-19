let timerInterval = null;
let timerSeconds = 300; // 기본 5분
let timerRunning = false;
let originalPresetSeconds = 300;

function updateTimerDisplay() {
    const min = Math.floor(timerSeconds / 60);
    const sec = timerSeconds % 60;
    const displayStr = `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    const displayEl = document.getElementById('timer-display-time');
    if (displayEl) {
        displayEl.textContent = displayStr;
    }

    // 10초 이하 남았을 때 긴박한 피드백 클래스 추가
    const wrapper = document.querySelector('.timer-modal-wrapper');
    if (wrapper) {
        if (timerRunning && timerSeconds <= 10 && timerSeconds > 0) {
            wrapper.classList.add('time-warning');
        } else {
            wrapper.classList.remove('time-warning');
        }
        
        // 완전히 완료되었을 때
        if (timerSeconds === 0) {
            wrapper.classList.add('time-finished');
        } else {
            wrapper.classList.remove('time-finished');
        }
    }
}

function toggleTimerModal() {
    const modal = document.getElementById('timer-modal');
    if (!modal) return;
    
    if (modal.classList.contains('active')) {
        closeTimerModal();
    } else {
        modal.classList.add('active');
        // 슬라이드 키 이벤트 방해 차단
        if (window.Reveal) {
            window.Reveal.configure({ keyboard: false });
        }
        updateTimerDisplay();
    }
}

function closeTimerModal() {
    const modal = document.getElementById('timer-modal');
    if (modal) {
        modal.classList.remove('active');
    }
    // 키 이벤트 복구
    if (window.Reveal) {
        window.Reveal.configure({ keyboard: true });
    }
}

function setTimerPreset(seconds) {
    stopTimer();
    timerSeconds = seconds;
    originalPresetSeconds = seconds;
    updateTimerDisplay();
}

function adjustTimerTime(delta) {
    timerSeconds += delta;
    if (timerSeconds < 0) timerSeconds = 0;
    updateTimerDisplay();
}

function toggleTimerStart() {
    if (timerRunning) {
        stopTimer();
    } else {
        startTimer();
    }
}

function startTimer() {
    if (timerSeconds <= 0) return;
    timerRunning = true;
    const startBtn = document.getElementById('timer-start-btn');
    if (startBtn) {
        startBtn.textContent = '일시정지';
        startBtn.classList.remove('play');
        startBtn.classList.add('pause');
    }
    
    updateTimerDisplay();
    
    timerInterval = setInterval(() => {
        if (timerSeconds > 0) {
            timerSeconds--;
            updateTimerDisplay();
        } else {
            triggerTimerEnd();
        }
    }, 1000);
}

function stopTimer() {
    timerRunning = false;
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    const startBtn = document.getElementById('timer-start-btn');
    if (startBtn) {
        startBtn.textContent = '시작';
        startBtn.classList.remove('pause');
        startBtn.classList.add('play');
    }
    updateTimerDisplay();
}

function resetTimer() {
    stopTimer();
    timerSeconds = originalPresetSeconds;
    updateTimerDisplay();
}

function triggerTimerEnd() {
    stopTimer();
    playTimerFinishedSound();
    
    // 시각적 완료 플래시 효과
    const wrapper = document.querySelector('.timer-modal-wrapper');
    if (wrapper) {
        wrapper.classList.add('flash-effect');
        setTimeout(() => {
            wrapper.classList.remove('flash-effect');
        }, 1500);
    }
}

function playTimerFinishedSound() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        
        // 브라우저 자동재생 제한 완화를 위해 상태 확인 후 재개
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        
        // 청아한 실로폰 멜로디 (도 - 미 - 솔 - 높은도: C5, E5, G5, C6)
        const playMelody = (startDelay) => {
            const freqs = [523.25, 659.25, 783.99, 1046.50]; // 도, 미, 솔, 도
            freqs.forEach((freq, idx) => {
                // 음 간격을 0.22초로 벌려서 스타카토 형식으로 명확하게 딩-동-댕-동 리듬을 줌
                const timeOffset = startDelay + (idx * 0.22);
                
                // 실로폰 특유의 맑고 가벼운 통울림을 위해 Triangle 파형 사용
                const osc = audioCtx.createOscillator();
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(freq, audioCtx.currentTime + timeOffset);
                
                // 실로폰의 금속성 맑은 고음 배음을 위해 1옥타브 위 Sine 파형 믹싱
                const oscOverTone = audioCtx.createOscillator();
                oscOverTone.type = 'sine';
                oscOverTone.frequency.setValueAtTime(freq * 2, audioCtx.currentTime + timeOffset);
                
                const gainNode = audioCtx.createGain();
                const gainOverToneNode = audioCtx.createGain();
                
                osc.connect(gainNode);
                oscOverTone.connect(gainOverToneNode);
                
                gainNode.connect(audioCtx.destination);
                gainOverToneNode.connect(audioCtx.destination);
                
                const now = audioCtx.currentTime + timeOffset;
                
                // 타격 순간(어택)은 극히 짧고 감쇄가 빠른 실로폰의 음량 엔벨로프
                gainNode.gain.setValueAtTime(0, now);
                gainNode.gain.linearRampToValueAtTime(0.3, now + 0.01); // 빠르게 타격
                gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.35); // 0.35초 동안 맑게 소멸
                
                gainOverToneNode.gain.setValueAtTime(0, now);
                gainOverToneNode.gain.linearRampToValueAtTime(0.1, now + 0.01);
                gainOverToneNode.gain.exponentialRampToValueAtTime(0.001, now + 0.18); // 배음은 더 빠르게 감쇄
                
                osc.start(now);
                oscOverTone.start(now);
                
                // 소리가 완전히 사라진 후 리소스 해제
                osc.stop(now + 0.4);
                oscOverTone.stop(now + 0.4);
            });
        };
        
        // 1.0초 간격을 두고 총 3회 연속 "딩동댕동" 재생 (0초, 1.0초, 2.0초)
        playMelody(0);
        playMelody(1.0);
        playMelody(2.0);
    } catch (e) {
        console.warn("웹 오디오 알림 출력 에러:", e);
    }
}

// 키보드 단축키 'T' 누르면 타이머 모달 토글
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
    }
    
    if (e.key === 't' || e.key === 'T') {
        e.preventDefault();
        toggleTimerModal();
    }
});
