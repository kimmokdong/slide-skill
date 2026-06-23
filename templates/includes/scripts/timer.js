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
            
            // 0초가 되는 즉시 알람을 울리도록 수정 (1초 지연 제거)
            if (timerSeconds <= 0) {
                triggerTimerEnd();
            }
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
        
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
        
        // 부드럽지만 크고 확실한 디지털 알람 소리 (빠른 삐빅- 삐빅-)
        const playBeep = (timeOffset) => {
            const osc = audioCtx.createOscillator();
            osc.type = 'sine'; // 부드러운 사인파 유지
            osc.frequency.setValueAtTime(980, audioCtx.currentTime + timeOffset); // 살짝 높은 음으로 잘 들리게
            
            const gainNode = audioCtx.createGain();
            
            osc.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            
            const now = audioCtx.currentTime + timeOffset;
            
            // 어택은 짧고 강하게, 릴리즈는 아주 짧게 끊어서 경쾌하게
            gainNode.gain.setValueAtTime(0, now);
            gainNode.gain.linearRampToValueAtTime(0.9, now + 0.01); // 최고 음량을 0.9로 대폭 상향
            gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.08); // 0.08초만에 아주 짧고 명확하게 소리 끊음
            
            osc.start(now);
            osc.stop(now + 0.1);
        };
        
        // 간격을 확 좁힌 삐빅 (0.0, 0.12) 쌍을 반복 (반복 주기도 0.8초로 좁혀서 긴박감)
        for (let i = 0; i < 5; i++) {
            playBeep(i * 0.8);        // 첫 번째 삐
            playBeep(i * 0.8 + 0.12); // 아주 짧은 간격 뒤 두 번째 빅
        }
    } catch (e) {
        console.warn("오디오 재생 에러:", e);
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
