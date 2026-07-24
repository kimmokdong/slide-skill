# Design Contract — Text-to-Slide-Architect (교육·연수 특화)

> **무엇인가**: AI 에이전트가 슬라이드를 생성할 때 지켜야 할 디자인 규약 단일 진실 원천(SSOT).
> **목적**: 학교 교사가 연수, 수업, 튜토리얼 등에서 사용하는 프레젠테이션을 **교육적으로 효과적이고 시각적으로 일관된** 품질로 보장합니다.
> **기준 해상도**: 16:9 와이드스크린 (가로 1280px × 세로 720px 기준)

---

## 1. 1장 1메시지와 텍스트 압축의 극단적 규율 (Text Compression)
- 한 슬라이드에 전달하려는 핵심 메시지는 **단 하나**입니다.
- **제목 (Title)**: 20자 이내. 현재 단계나 핵심 메시지 명시 (글씨 크기: 60~72px)
- **본문 (Bullets)**: 슬라이드당 최대 3개, 각 20자 이내로 압축.
- **강조 텍스트 (Strong Text)**: 청중의 시선을 사로잡을 핵심 단어나 어구 1~2개(주로 핵심 명사구)는 반드시 `<strong>` 태그로 래핑하여 표시해야 합니다. (과도한 래핑 금지, 슬라이드당 1~2개 수준으로 엄격 제한)
- **무손실 원칙**: 20자가 넘어가는 긴 설명, 부연, 대본은 **반드시 `SPEAKER_NOTES` 항목으로 밀어내야** 합니다.

## 2. 컬러 및 디자인 규율 (Color Discipline 60-30-10)
에이전트는 프레젠테이션을 생성할 때 60-30-10 컬러 비율을 엄격히 준수합니다.
- **순도 100% 원색 절대 금지** (예: 완전한 빨강 #FF0000). 부드러운 파스텔톤이나 Muted 톤을 사용하세요.
- `bg` (60%): 순백색 또는 극도로 옅은 톤
- `bg_secondary` / 구조색 (30%): 연한 웜그레이 등 (박스, 배경 구분용)
- `accent` (10%): 핵심 강조용 포인트 컬러 (단 1~2가지만 채도 높게)

## 3. Layout (레이아웃 컴포넌트)
자유 형식보다는 사전 정의된 컴포넌트를 활용해야 합니다. 단순 글머리기호의 나열을 최소화하세요.
- **절차/순서:** `roadmap` (3~5단계 절차 카드, 기본 4단계 권장)
- **시간 흐름/상태 변화:** `timeline` (`date`, `title`, `desc` 기반 시간축)
- **분류/비교:** `matrix` (2x2 분류), `vs_ox` (O/X 대비), `comparison`
- **스크린샷 튜토리얼:** `tutorial` (좌 텍스트 + 우 이미지 50:50 분할, 상단 스텝퍼)
- **핵심 요약:** `summary` (`title`, `desc` 기반 요약 리스트)
- **실습 안내:** `hands_on`

## 4. 정보 흐름과 네비게이션 (Wayfinding)
스크린샷이 연속으로 이어지면 학습자는 전체 맥락을 잃기 쉽습니다.
- **스텝퍼(Stepper)**: 최상단 여백에 전체 프로세스 단계를 표시 (현재 Active, 완료 Inactive)
- **섹션 헤더 (SECTION_HEADER)**: 슬라이드 좌상단에 현재 어떤 대주제를 이야기하고 있는지 이정표를 명시
- **하단 핵심 요약 (BOTTOM_TAKEAWAY)**: 슬라이드 내용이 아무리 길어도 단 1줄의 핵심 명제를 슬라이드 하단에 배치
- **아이콘 불릿 (Icon Bullets)**: 불릿 포인트를 작성할 때는 이모지/아이콘(`icon`)을 동반하여 시각적 직관성 확보

## 5. 스크린샷 처리 (Screenshot Handling)
- **1장 1액션**: 한 슬라이드에 1~2번의 조작 과정만 담으세요.
- **프레임 씌우기**: 날것의 캡처 이미지에 브라우저 창/모바일 틀을 씌워 정돈된 느낌을 줍니다.
- **시선 유도 (Highlighting)**: 
  - ① 딤밍(Dimming): 화면을 반투명으로 덮고 클릭할 부분만 뚫기
  - ② 포인트 박스: 조작 위치에 빨간/형광 테두리와 순서 번호 배지
  - ③ 확대(Zoom-in): 작은 메뉴를 원형으로 확대

## 6. Motion (모션 및 애니메이션)
- 슬라이드 전환은 기본 전환(`slide`, `fade`)만 사용합니다. 복잡한 모션 금지.
- 강조 박스나 화살표는 강사가 설명할 때 정확한 타이밍에 맞춰 **나타내기(Fade)** 되도록 제어합니다.

## 7. Voice (보이스 및 톤)
- **Summary 모드 (기본)**: "~해 볼까요?", "~을 확인해 보겠습니다" (부드러운 청유형)
- **Fidelity 모드**: "~임", "~현황" (단정적, 간결한 명사형)

## 8. Anti-patterns (절대 금지 사항)
- ❌ **글씨 꽉 채우기**: 본문이 넘치면 무조건 `SPEAKER_NOTES`로 분리!
- ❌ **표를 텍스트로 뭉개기**: 중요한 표를 불릿 항목으로 뭉뚱그리지 마세요.
- ❌ **가짜 수치 (Hallucination)**: 출처 없는 수치를 지어내지 말고, 검색을 통해 팩트체크하세요.
- ❌ **날것의 캡처 나열**: 하이라이트, 스텝퍼 없이 스크린샷만 연속으로 나열하지 마세요.
- ❌ **텍스트 최소 크기 위반**: 어떤 텍스트도 18px 미만으로 내려가면 안 됩니다.

## 9. 테마 스타일링 계약 (Theme Styling Interface) 및 에셋 전략
어떤 테마(동적/고정 테마 포함)가 적용되더라도 슬라이드의 기본 틀(HTML 레이아웃 크기 및 배치)은 유지하며, 오직 아래 명세된 **‘테마 제어 필수 요소’**들의 CSS 및 에셋 매핑을 통해서만 비주얼 차별화를 극대화합니다.

### 9-1. 테마 제어 필수 요소 명세
1. **슬라이드 캔버스 배경 (Slide Canvas Background)**: 전체 배경색뿐 아니라, 테마별 연한 보조선 격자 패턴(모눈종이 격자, 디지털 HUD 격선, 사선 가이드라인 등)을 투명도 8%~15% 수준으로 오버레이합니다.
2. **콘텐츠 카드/박스 (Content Card/Box)**: 본문을 담는 상자의 테두리 스타일(Dashed/Solid), 모서리 둥글기(Radius), 그림자 깊이(Shadow), 투명도 및 블러(Glassmorphism)를 제어합니다.
3. **타이포그래피 및 강조 (Typography & Highlights)**: 제목/본문 글꼴(Font family)과 텍스트 내 강조 단어(`<strong>` 등)에 씌워지는 시각적 형태(형광펜 효과, 디지털 괄호 등)를 통일성 있게 지정합니다. 에이전트는 본문 핵심 키워드를 자동으로 `<strong>` 태그로 감싸 렌더러가 테마별 강조 스타일을 적용할 수 있도록 설계해야 합니다.
4. **이정표 영역 (Wayfinding UI)**: 상단 스텝퍼(Stepper), 좌상단 섹션 헤더(Section Header), 하단 핵심 요약 띠(Bottom Takeaway)의 스킨 및 강조색을 제어합니다.
5. **이미지 프레임 프리셋 (Image Frame Preset)**: 이미지/스크린샷 영역에 적용되는 브라우저 창 또는 모바일 기기 모형의 외곽 디자인(Radius, Border, Shadow) 및 상단부 컨트롤러(신호등 도트 등) 노출 방식(cute, tech, business, retro, minimal)을 제어합니다.

### 9-2. 아이콘 및 이미지 에셋 공급 전략 (1, 3번 하이브리드)
1. **아이콘 (Lucide Vector Icons + CSS 스타일링)**:
   - HTML 내의 아이콘은 가볍고 확장성이 우수한 **Lucide Icons**를 표준으로 사용하며 CDN을 통해 렌더링합니다.
   - 테마에 따라 아이콘의 두께(`stroke-width`), 네온 발광(`filter: drop-shadow(...)`), 배경 배지 디자인(원형/각진형/그레이형)을 CSS만으로 스위칭합니다.
2. **삽화 이미지 (AI 실시간 투명 일러스트 생성)**:
   - 슬라이드 1장을 대변하는 정교한 설명용 삽화가 필요할 시, 사용 가능한 이미지 생성 도구로 배경이 투명한(Transparent PNG) 고품질 일러스트를 제작해 배치합니다.

### 9-3. `meta.theme_colors` 표준 키 명세
테마 에디터와 HTML 렌더러가 공유하는 표준 키는 아래 이름을 사용합니다. `icon_style_preset`처럼 과거 명칭을 새로 만들지 말고 `icon_preset`으로 통일합니다.

```json
{
  "bg": "#F8FAFF",
  "bg_secondary": "#EEF2FF",
  "text": "#1E293B",
  "text_secondary": "#64748B",
  "accent": "#4F46E5",
  "accent_secondary": "#7C3AED",
  "card_style_preset": "business_clean",
  "icon_preset": "business",
  "font_preset": "friendly",
  "highlight_style": "friendly",
  "takeaway_style": "friendly",
  "motion_preset": "friendly",
  "image_frame_preset": "business",
  "bg_pattern_style": "grid",
  "decorations": ["corner_accent"]
}
```

### 9-4. 레이아웃별 데이터 스키마 표준 키 명세
에이전트가 `slide_plan.json`을 작성할 때 템플릿 렌더러가 올바르게 인식하도록 아래 레이아웃별 고유 키 매핑을 엄격히 준수해야 합니다. 임의로 키를 축약하거나 변경해서는 안 됩니다.
1. **`stats` (통계/수치)**:
   - **`STAT_ITEMS`** (`STATS_ITEMS` 금지) ➔ 각 항목은 `value`, `label`, `kind`를 사용합니다.
   - `kind`는 `ratio`, `rank`, `count`, `comparison` 중 하나입니다. 게이지는 `ratio`와 `comparison`에만 사용하며, `comparison`은 비교 기준을 나타내는 `percentage`를 함께 지정합니다.
   - `kind`를 생략하면 `%`·점수는 `ratio`, `위`·순위 라벨은 `rank`, 나머지는 `count`로 추론합니다. 순위와 단순 인원 수에 임의 게이지를 붙이지 않습니다.
2. **`quiz` (퀴즈/질문)**:
   - **`QUESTION`** (`QUIZ_QUESTION` 금지) ➔ 질문 내용 문자열
   - **`QUIZ_OPTIONS`** ➔ 보기 배열. 각 항목은 객체 또는 단순 문자열 (예: `["O", "X"]` 또는 `[{"text": "보기1"}, {"text": "보기2"}]`)
   - **`ANSWER_INDEX`** ➔ 0부터 시작하는 정답 인덱스 숫자
3. **`vs_ox` (2단 대비/O-X 확장형)**:
   - **`O_TITLE`** / **`X_TITLE`** ➔ 각 컬럼의 헤더 명칭
   - **`O_MARKER`** / **`X_MARKER`** ➔ 각 컬럼의 헤더 및 기본 항목 마커. 생략 시 각각 `⭕`, `❌` 사용. 장점/단점은 `👍`/`👎`, 권장/비권장은 `✅`/`⛔`, Before/After는 `Before`/`After`처럼 맥락에 맞게 지정 가능
   - **`O_ITEMS`** / **`X_ITEMS`** ➔ 대비되는 항목 리스트 배열. 각 항목은 `{"text": "내용"}` 또는 개별 마커가 필요한 경우 `{"marker": "✅", "text": "내용"}` 형태
4. **`matrix` (분류 매트릭스)**:
   - **`MATRIX_ITEMS`** ➔ 매트릭스 셀 배열. 각 항목은 `{"icon": "📝", "label": "라벨", "desc": "설명"}` 형태
5. **`roadmap` / `timeline` (순서/절차)**:
   - **`ROADMAP_ITEMS`** ➔ 절차 카드 배열. 각 항목은 `{"label": "라벨", "desc": "설명"}` 형태
   - **`TIMELINE_ITEMS`** ➔ 시간축 카드 배열. 각 항목은 `{"date": "시점", "title": "제목", "desc": "설명"}` 형태
   - `roadmap`은 3~5개를 허용하고 기본 4개를 권장합니다. `timeline`은 3~6개를 허용하며 4개 이하는 가로 rail, 5개 이상은 compact 구조로 렌더링됩니다.
6. **`summary` (핵심 요약)**:
   - **`SUMMARY_ITEMS`** ➔ `{"title": "요약 제목", "desc": "설명"}` 객체 배열을 권장합니다. 짧은 문자열 배열도 허용합니다.
7. **`closing` (마무리)**:
   - **`MESSAGE`** ➔ 마무리 문장
   - **`CTA`** ➔ 행동 유도 문구
   - **`BULLET_ITEMS`** ➔ 필요 시 마지막 체크리스트
8. **`tutorial` / `hands_on` (실습/순서)**:
   - **`STEPPER_ITEMS`** ➔ 상단 내비게이션 스텝 배열. 각 항목은 `{"label": "단계명", "state": "completed/active/inactive"}` 형태
   - **`STEP_NUMBER`** ➔ 현재 활성화된 단계 번호 문자열 (예: `"1"`)
   - **`BULLET_ITEMS`** ➔ 좌측 실습 단계 리스트
   - **`TIP`** / **`WARNING`** / **`DURATION`** ➔ 보조 안내 팁, 경고, 예상 소요 시간
   - **`RESULT_TEXT`** ➔ `hands_on`에서 예상 결과 캡션
9. **활동 문항 (`activities[].worksheet_block`)**:
   - `ox_check`는 문제판에서 시작해 클릭마다 한 문항의 큰 O/X와 해설을 집중 공개합니다. 학생용에는 해설을 넣지 않고, 교사용은 한 페이지에 최대 4문항을 배치합니다.
   - `cloze_word_bank.word_bank`는 인쇄물과 슬라이드가 공유하는 고정 표시 순서입니다. `sentences[].answer` 순서와 다르게 섞어 저장하며 실행 중 재무작위화하지 않습니다.


