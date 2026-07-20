---
name: slide
description: 사용자의 거친 아이디어나 시나리오 텍스트를 기승전결 있는 풍부한 프레젠테이션(HTML/PPTX)으로 자동 생성하는 스킬입니다. slide_plan.json 기반의 중간 설계도(SSOT) 아키텍처, 리서치 검증, 네이티브 PPTX 변환을 지원합니다.
---

# Slide Skill

이 스킬은 사용자가 텍스트를 던져주면, 에이전트가 알아서 기승전결 구조화, 웹 리서치 검증, 이미지/도식 생성 후 **중간 설계도(slide_plan.json)**를 작성하고, 이를 바탕으로 완벽한 **HTML 프리뷰와 편집 가능한 네이티브 PPTX**를 만들어내는 종합 프레젠테이션 컴파일러 워크플로우입니다.

---

## 🏗️ 아키텍처 및 폴더 구조 (SSOT 기반)

에이전트는 **HTML을 직접 하드코딩하지 않습니다.** 모든 슬라이드의 내용은 반드시 `slide_plan.json`에 작성하며, 파이썬 스크립트가 이를 읽어 HTML과 PPTX를 생성합니다.

> ⚠️ **중요 규칙**: 출력물 폴더(`{YYMMDD}_{영문프로젝트명}`)는 절대 스킬 폴더(`slide`) 안에 생성하지 마세요. 사용자가 현재 작업 중인 루트 폴더(예: 슬라이드 제작 전용 폴더)에 바로 생성해야 합니다. 스킬의 스크립트를 실행할 때는 스킬 폴더의 절대 경로를 참조하세요.

```
{사용자의 작업 루트}/ (예: 바탕화면/슬라이드제작/)
├── references/                      ← 공용 레퍼런스 및 디자인 규약
│   └── design-contract.md           ← [필독] 디자인 및 문장 작성 규약서
├── {YYMMDD}_{영문프로젝트명}/      ← 개별 프로젝트 폴더 (예: 260615_sociogram_workshop)
│   ├── slide_context.yaml           ← 설정 (필수 변수 7개 + 모드)
│   ├── raw_script.md                ← 사용자 원문 텍스트
│   ├── slide_plan.json              ← [핵심] 에이전트가 작성하는 단일 진실 원천(SSOT)
│   ├── assets/                      ← 사용자가 본인의 이미지/에셋을 넣는 공간
│   └── output/                      ← 생성된 슬라이드 출력물
│       ├── index.html               ← build_html.py가 생성
│       ├── presentation.pptx        ← export_image_pptx.py가 통이미지로 생성
│       ├── images/                  ← 사용자가 제공한 원본 복사본 및 AI 생성 이미지
│       └── diagrams/                ← Mermaid 다이어그램 (SVG)
```

---

## 📋 전체 워크플로우 (순서 엄수)

```
[모듈 0] 사전 컨텍스트 (Intake) → [모듈 1] 레퍼런스 파싱 및 리서치 보강
→ [모듈 2] 모드 분기 및 서사 구조화 → [모듈 2.5] 수업 활동 설계(content_blueprint/activities)
→ [모듈 3] Deck Planner (slide_plan.json 작성)
→ [모듈 4] 도식/이미지 에셋 생성 → [모듈 5] HTML 렌더링 및 검수 → [모듈 6] 최종 파일(PPTX) 추출
```

---

## 모듈 0: 사전 컨텍스트 수집 (Intake Process)

**[최우선 필수 작업]** 사용자가 제공한 원본 대본이나 시나리오 메모 텍스트는 유실되지 않도록 반드시 프로젝트 폴더 내에 `raw_script.md` 파일로 가장 먼저 저장해 두어야 합니다.

**[핵심 워크플로우 규칙]** 사용자가 `/slide` 스킬을 호출하면, 에이전트는 기획안(implementation_plan) 작성 전 **무조건 `ask_question` 도구를 호출하여 사용자에게 모달창(UI)을 띄워 필수 정보를 물어보아야 합니다.**
이 모달창 질의응답 과정이 이 스킬 파이프라인의 **가장 핵심적인 단계**입니다. 사용자가 명시하지 않은 정보를 에이전트가 임의로 가정하여 넘기지 말고, 반드시 모달창을 통해 선택지를 제공하세요.

**Codex 호환 규칙**: `ask_question` 도구가 없는 Codex 환경에서는 `request_user_input`이 있으면 그것을 사용하고, 둘 다 없으면 일반 채팅으로 아래 필수 항목을 질문한 뒤 답변 전까지 생성하지 않습니다. 사용자가 명시적으로 "기본값으로 진행"이라고 말한 경우에만 기본값을 적용합니다.

### 0-A. 모달창(`ask_question`) 필수 질문 항목
에이전트는 `ask_question` 도구의 단일/다중 선택 기능(`is_multi_select`)을 활용하여, 아래의 필수 변수들을 사용자가 클릭으로 편하게 선택할 수 있도록 모달창을 띄워야 합니다.

1. `audience_level` (대상 수준): 초등학교 저학년 / 고학년 / 중고등 / 성인 등
2. `lecture_duration_min` & `slide_count` (강의 시간 및 예상 장수): 10분(5장) / 40분(15장) 등 묶어서 질문
3. `tone` (톤앤매너): 공식적이고 진지하게 / 친근하고 부드럽게 / 유머러스하게
4. `theme_preference` (테마 선택): AI 동적 맞춤 테마 / 귀여운 바인더 노트(cute_note) / 공공·기술(tech_blue) / 따뜻한 교육(warm_edu)
5. **학습지 활동 추가 여부 (다중 선택 가능)**: 
   - [ ] ❌ 학습지 제외 (슬라이드만 생성)
   - [ ] 빈칸 채우기 (`cloze_word_bank`)
   - [ ] 선 잇기 (`matching_lines`)
   - [ ] 표 채우기 (`table_fill`)
   - [ ] 짧은 답 쓰기 (`short_answer`)
6. **외부 영상 사용 여부 (단일 선택)**:
   - ( ) 사용 안 함
   - ( ) 유튜브 링크 직접 입력 (입력 시 URL 문자열 받기)
   - ( ) **에이전트가 자동 검색 및 추천** (선택 시, 에이전트가 주제에 맞춰 유튜브를 검색하여 상위 영상을 묻는 2차 모달창을 띄웁니다.)
7. **영상 표시 방식 (단일 선택, 영상을 사용하는 경우)**:
   - ( ) 링크 카드 (기본값)
   - ( ) 슬라이드 안에 임베드 (iframe)
8. **영상 연결 위치 (단일 선택, 영상을 사용하는 경우)**:
   - ( ) AI가 자동 추천
   - ( ) 도입에 넣기
   - ( ) 활동 전에 넣기
   - ( ) 정리 단계에 넣기
9. **개인 소장 이미지(사진, 캡처본 등) 사용 여부 (단일 선택)**:
   - ( ) 사용 안 함 (AI가 알아서 일러스트/도식 생성)
   - ( ) 사용함 (직접 준비한 이미지 파일들을 넣을 예정)

### 0-A-2. 사용자 이미지 투입 대기 워크플로우 (모달창에서 '사용함' 선택 시)
1. 에이전트는 즉시 프로젝트 폴더 내에 `assets/` 폴더를 생성합니다.
2. 다음 모듈(slide_plan.json 작성)로 바로 넘어가지 않고, 채팅창을 통해 사용자에게 *"assets/ 폴더가 생성되었습니다. 사용하실 이미지 파일들을 해당 폴더에 넣으신 후 '다 넣었어'라고 말씀해 주세요."*라고 안내한 뒤 **대기(Stop)**합니다.
3. 사용자가 이미지를 다 넣었다고 답변하면, 기존의 '이미지 에셋 풀 매핑 규칙(0.5)'을 발동하여 배치 작업을 시작합니다.

### 0-A-3. 유튜브 자동 검색 워크플로우 (모달창에서 자동 검색 선택 시)
1. 에이전트는 사용자의 주제에 맞는 검색어를 생성합니다. (예: "가짜뉴스 구별법 초등")
2. `scripts/search_youtube.py "[검색어]"` 스크립트를 실행하여 결과를 JSON으로 받습니다.
3. **2차 모달창(`ask_question`)**을 띄워 검색된 상위 영상 3~5개를 선택지로 제공합니다.
   - 예시: `1. [제목] (채널: OO, 3분 20초) - 1,500회 시청`
4. 사용자가 선택한 영상의 URL을 추출하여 `media` 객체의 `url` 필드에 매핑합니다.

모달창을 통해 사용자의 선택을 모두 응답받은 직후에만 다음 모듈로 넘어가며, 수집된 응답은 `slide_context.yaml`에 저장됩니다.

> ⚠️ **중요 (활동과 슬라이드의 1:1 페어링)**: 학생용 학습지 문항마다 발표 흐름에 `layout: "activity"` 슬라이드를 정확히 한 장 배치합니다. 이 한 장이 처음에는 문항을 보여 주고, 클릭하면 같은 화면에서 정답을 공개합니다.

**단일 활동 슬라이드 원칙**: `activity_prompt`와 유형별 `*_reveal`을 별도 페이지로 작성하지 않습니다. 활동 데이터는 최상위 `activities[].worksheet_block`에 한 번만 정의하고, 발표 슬라이드는 `ACTIVITY_REF`, 활동지와 정답지는 `ACTIVITY_REFS`로 참조합니다. 별도의 활동 안내가 꼭 필요한 수업만 `activity_instruction`을 추가합니다. `reflection_checklist`는 정답이 없으므로 기본적으로 수업 슬라이드와 정답지에 넣지 않습니다.

**빈칸 채우기 상호작용**: `cloze_word_bank` 활동은 보기 단어를 클릭하면 같은 `data-word`의 빈칸으로 이동시키는 수업용 확인 화면으로 렌더링됩니다. `word_bank` 배열과 `sentences`의 `{ "text": "문장 [정답]", "answer": "정답" }` 형식을 함께 사용합니다. OX 형식 데이터나 보기 없는 빈칸 화면은 빌드 검증에서 실패시킵니다.

**교사용 정답지 완전성**: `answer_key` 페이지가 있으면 학생용 학습지의 `ox_check`, `cloze_word_bank`, `matching_lines`, `table_fill`, `short_answer` 문항 유형별 수를 모두 포함해야 한다. `reflection_checklist`는 정답지가 필요 없다.

### 0-B. 초기 파일 생성
수집한 답변은 프로젝트 폴더의 세 파일로 반드시 먼저 고정합니다.

```txt
raw_script.md
slide_context.yaml
slide_plan.json
```

반복 가능한 초기화를 위해 로컬 스킬의 helper를 사용할 수 있습니다.

```bash
 python ".agents/skills/slide/scripts/init_lesson_project.py" --answers answers.json
```

`--answers`를 생략하면 터미널에서 질문을 순서대로 묻습니다. Codex의 질문 UI를 사용할 수 있는 환경에서는 먼저 사용자에게 질문하고, 답변을 `answers.json` 또는 동등한 내부 데이터로 정리한 뒤 위 helper와 같은 구조의 파일을 생성합니다.

`answers.json` 예시:

```json
{
  "project_name": "fake_news_lesson",
  "raw_script": "초등 5학년 국어 수업. 주제는 가짜뉴스를 구별하는 방법.",
  "audience_level": "초등 5학년",
  "grade": "초등 5학년",
  "subject": "국어",
  "topic": "가짜뉴스를 구별하는 방법",
  "duration_minutes": 40,
  "slide_count": 5,
  "tone": "친근",
  "category": "교과교육",
  "presentation_mode": "대면",
  "theme_preference": "AI 알아서 맞춤",
  "goal": "정보의 출처와 근거를 확인할 수 있다.",
  "big_question": "이 정보는 믿어도 될까?",
  "activity_title": "가짜뉴스 구별 OX 퀴즈",
  "work_time_minutes": 2
}
```

### 0.5. 이미지 에셋 풀(Asset Pool) 처리 지침 및 재배치 규칙
사용자가 연수 자료에 들어갈 이미지들을 프로젝트 폴더 내 `assets/` 에 미리 업로드해 둔 경우, 아래 규칙을 철저히 엄수하여 오배치를 방지합니다.

#### ✅ 이미지 배치 필수 체크리스트 (오배치 방지)

**[STEP 1] 이미지 에셋 목록 먼저 스캔**
- 배치 작업 전, `assets/` 폴더의 **모든 파일명 목록을 먼저 `list_dir`로 확인**합니다.
- 파일명이 한글이든 영문이든, 이름에 담긴 핵심 키워드를 추출합니다. (예: `인기도 랭킹.jpg` → 키워드: "인기도", "랭킹")

**[STEP 2] 슬라이드 전체 훑기 (1:1 매칭표 작성)**
- 파일명 키워드를 기준으로, **모든 슬라이드의 TITLE·BODY·SPEAKER_NOTES**를 순서대로 읽으며 가장 연관성이 높은 슬라이드를 찾습니다.
- 이 과정을 반드시 서면으로 정리합니다 (예: `인기도 랭킹.jpg` → 슬라이드 24 "실시간 정보 렌더링 화면(AdminTV)").
- 이전 대화에서 "특정 슬라이드에 특정 이미지"를 지시받은 내용이 있더라도, **전체 재배치 요청이 들어오면 그 지시는 리셋**하고 전체 맥락에서 재검증합니다.

**[STEP 3] 기존 매핑 초기화 (전체 재배치 시)**
- 사용자가 "어울리는 곳에 전체 재배치해줘"라고 요청한 경우:
  1. `slide_plan.json` 전체를 읽어 현재 `IMAGE_SRC`가 설정된 슬라이드 목록을 파악합니다.
  2. **모든 기존 이미지 경로를 기본 이미지(`images/demo_tutorial.png`)로 일괄 초기화**합니다.
  3. STEP 2에서 작성한 1:1 매칭표를 기준으로 새로운 배치를 적용합니다.
- 불완전한 상태로 덮어씌우는 기계적 배치를 절대 금지합니다.

**[STEP 4] 복사 및 파일명 변환**
- 원본 이미지를 `{프로젝트폴더}/output/images/` 폴더로 복사합니다.
- 한글 파일명이 경로 오류를 일으킬 수 있으므로, 복사 시 영문 스네이크케이스로 변환합니다. (예: `인기도 랭킹.jpg` → `popularity_ranking.jpg`)
- `slide_plan.json`의 `IMAGE_SRC`는 변환된 영문 파일명으로 기록합니다.

#### ⚠️ 오배치 발생 원인 3가지 (절대 반복 금지)
1. **컨텍스트 고정**: 이전 대화의 구체적 지시가 전체 재배치 작업에도 그대로 이어지는 오류
2. **미초기화 덮어쓰기**: 기존 이미지 경로를 전면 초기화하지 않고 일부만 수정하는 오류
3. **파일명 무시**: 파일명의 핵심 키워드를 슬라이드 본문과 대조하지 않고 임의 순서로 배치하는 오류

---

## 모듈 1: 레퍼런스 파싱 및 리서치 보강

### 1-1. 문서 파싱
- 기존 PPTX/PDF가 있다면 `parse_pptx.py` 또는 `parse_pdf.py`로 텍스트를 추출해 읽어들입니다.

### 1-2. 리서치 보강 (Research)
- 사용자의 원문에 수치, 통계, 외부 사례가 포함된 경우 사용 가능한 웹 검색 도구를 통해 팩트체크를 진행합니다.
- 부족한 사례나 뒷받침할 만한 최신 통계를 검색하여 덧붙입니다.
- **가짜 수치(Hallucination) 절대 금지**: 출처가 없는 수치는 삭제하고, 검색된 검증된 수치만 슬라이드에 넣습니다.

---

## 모듈 2: 모드 분기 (Fidelity vs Summary) 및 서사 구조화

입력된 문서 성격에 따라 처리 모드를 결정합니다.

| 모드 | 대상 문서 | 처리 원칙 |
|------|---------|---------|
| **Fidelity 모드** | 제안서, 기안서, 공식 보고서 | 원문의 순서와 내용을 최대한 보존. 표는 분할하되 뭉개지 않음. |
| **Summary 모드** | 강의 원고, 연수 대본, 에세이 | 교육학적 기승전결 구조로 재배치. 핵심만 남기고 과감히 압축. |

사용자에게 **"목차(개요) 및 모드"**를 보여주고 승인을 받습니다.

---

## 모듈 2.5: 수업 활동 설계 (Lesson Activity Blueprint)

학생용 활동지가 필요한 수업형 자료는 `slides`만 바로 만들지 말고 아래 흐름을 따릅니다.

```txt
user_input → content_blueprint → activities(SSOT) → pages(refs) → slide + worksheet + answer_key
```

`content_blueprint`는 수업 전체의 목표, 큰 질문, 단계별 교사/학생 행동, 학습지 역할을 담는 공통 설계도입니다. `activities`는 문항·정답·교사 발문을 한 번만 보관하는 실제 수업 단위입니다.

학습지가 있는 자료는 `slide_plan.json`에 기존 `slides` 대신 `pages`를 사용합니다. 문항 데이터의 SSOT은 `activities`이며 `pages`에는 참조만 둡니다. 렌더러는 기존 `slides`와 `activity_packages`도 호환 입력으로 계속 지원합니다.

```json
{
  "activities": [{
    "id": "activity_1",
    "title": "활동 1. 선 잇기",
    "worksheet_block": {
      "block_type": "matching_lines",
      "title": "알맞은 것끼리 연결하기",
      "pairs": [{"left": "재규어", "right": "아마존 열대우림"}]
    }
  }],
  "pages": [
    {"page_type": "slide", "layout": "activity", "ACTIVITY_REF": "activity_1"},
    {"page_type": "worksheet", "ACTIVITY_REFS": ["activity_1"]},
    {"page_type": "answer_key", "ACTIVITY_REFS": ["activity_1"]}
  ]
}
```

지원 `page_type`:
- `slide`: 기존 16:9 발표 슬라이드
- `worksheet`: A4 학생용 활동지
- `answer_key`: A4 교사용 정답지

출력 모드:
- 기본 URL: 발표 모드, `slide`만 표시
- `?mode=teacher`: 슬라이드 + 학습지 + 정답지 모두 표시
- `?mode=worksheet`: 학습지/정답지 확인 및 인쇄용

초기 학습지 블록은 `short_answer`, `ox_check`, `cloze_word_bank`, `matching_lines`, `table_fill`, `reflection_checklist`를 허용합니다.
**주의사항**: 학습지 블록을 JSON에 넣을 때는 슬라이드처럼 `"type"`을 쓰면 안 되며, 반드시 **`"block_type"`** 키를 사용해야 합니다.

### 📝 학습지 블록(Worksheet Block) 스키마 사전 (SSOT)
학습지(`page_type: "worksheet"` 또는 `"answer_key"`) 내부의 `BLOCKS` 배열에 들어갈 각 활동 블록의 필수 구조입니다. **아래 변수명과 구조를 100% 동일하게 사용하세요.**

#### 1. 단답형 (short_answer)
```json
{
  "block_type": "short_answer",
  "title": "질문 제목",
  "instruction": "안내문",
  "answer_lines": 2,
  "sample_answer": "예시 답안"
}
```
#### 2. OX 퀴즈 (ox_check)
```json
{
  "block_type": "ox_check",
  "title": "OX 퀴즈 제목",
  "items": [
    {"statement": "질문 1", "answer": "O", "explanation": "해설 1"}
  ]
}
```
#### 3. 빈칸 채우기 (cloze_word_bank)
```json
{
  "block_type": "cloze_word_bank",
  "title": "빈칸 채우기",
  "word_bank": ["단어1", "단어2"],
  "sentences": [
    {"text": "이것은 [단어1] 입니다.", "answer": "단어1"}
  ]
}
```
*(빈칸은 반드시 `[ ]`로 감싸서 표기)*

#### 4. 선 잇기 (matching_lines)
```json
{
  "block_type": "matching_lines",
  "title": "알맞게 이어보세요",
  "pairs": [
    {"left": "사과", "right": "빨갛다"},
    {"left": "바나나", "right": "노랗다"}
  ]
}
```

#### 5. 표 채우기 (table_fill)
```json
{
  "block_type": "table_fill",
  "title": "표 채우기",
  "headers": ["증상", "올바른 대처", "잘못된 대처"],
  "rows": [
    [
      {"text": "열이 날 때", "is_blank": false}, 
      {"text": "푹 쉰다", "is_blank": true}, 
      {"text": "뛰어논다", "is_blank": false}
    ]
  ]
}
```
*(`is_blank: true`인 셀은 학생용 학습지에서 빈칸으로 렌더링됩니다)*

#### 6. 자기 점검 체크리스트 (reflection_checklist)
```json
{
  "block_type": "reflection_checklist",
  "title": "스스로 점검하기",
  "items": [
    {"text": "수업에 열심히 참여했나요?"}
  ]
}
```

### 외부 미디어(YouTube) 연결 규칙
표준 `pages` 구조에서는 영상 자체를 독립 `slide`로 작성합니다. 영상은 활동 안내나 학생용 문항 화면 안에 넣지 않으며, 활동과 연결되는 경우에도 영상 슬라이드 다음에 `activity` 슬라이드를 배치합니다.
```json
{
  "page_type": "slide",
  "layout": "video_hook",
  "TITLE": "영상 제목",
  "EMBED_URL": "https://www.youtube.com/embed/VIDEO_ID",
  "PURPOSE": "수업 도입에서 문제 상황을 찾아봅시다.",
  "STUDENT_TASK": "영상을 보고 의심되는 정보 표현을 한 가지 적습니다."
}
```
- 교실에서 바로 재생할 영상은 `video_hook`, 외부 창에서 여는 영상은 `video_link_card`를 사용합니다.
- `activity_instruction`은 시간·준비물처럼 별도 안내가 꼭 있을 때만 추가합니다. 단순히 영상을 보여 준다는 이유로 추가하지 않습니다.
- 레거시 `activity_packages[].media` 입력은 호환을 위해 계속 지원하며 `video_hook` 또는 `video_link_card`로 변환됩니다.

---

## 모듈 3: Deck Planner (slide_plan.json 작성) ⭐ 핵심

확정된 목차를 바탕으로 에이전트는 `slide_plan.json` 파일을 작성합니다.
**반드시 `references/design-contract.md`의 규칙을 준수하세요.**

### ⚡ 동적 테마 시스템 (Dynamic Theme)
에이전트는 사용자의 **발표 주제를 분석**하여, 주제에 가장 어울리는 컬러와 장식 요소를 스스로 결정합니다. 
모든 결정 사항은 `references/design-contract.md`에 명시된 **테마 스타일링 계약(Theme Styling Interface)**에 부합하도록 매핑됩니다.

#### 테마 결정 5단계:
1. **주제 분석**: 발표 주제의 분위기(교육, 기술, 안전, 건강 등)를 파악
2. **60-30-10 컬러 추출**: 주제에 어울리는 세련된 배경색(60%), 텍스트/구조색(30%), 포인트 강조색(10%)의 HEX 코드를 추출 (원색 금지, Muted/Pastel 톤 권장)
3. **배경 패턴 및 장식 선택**: 주제에 맞는 CSS 배경 장식(`decorations`) 및 은은한 배경 패턴 스타일(`bg_pattern_style`: grid/dots/diagonal)을 투명도 8%~15% 수준으로 선택
4. **아이콘 스타일 프리셋 선택**: 주제의 톤앤매너에 어울리는 아이콘 두께와 효과 프리셋(`icon_preset`: cute/tech/business/minimal_raw/handdrawn)을 설정
5. **이미지 프레임 프리셋 선택**: 스크린샷 튜토리얼 영역의 프레임 디자인 프리셋(`image_frame_preset`: cute/tech/business/retro/minimal)을 설정

#### `meta.theme_colors` 스키마:
```json
"theme_colors": {
    "bg": "#F0F4FF",
    "bg_secondary": "#E2E8F0",
    "text": "#1E293B",
    "text_secondary": "#64748B",
    "accent": "#3B82F6",
    "accent_secondary": "#7C3AED",
    "card_style_preset": "business_clean",
    "icon_preset": "business",
    "font_preset": "friendly",
    "highlight_style": "friendly",
    "takeaway_style": "friendly",
    "motion_preset": "friendly",
    "image_frame_preset": "business",
    "bg_pattern_style": "grid",
    "decorations": ["corner_accent", "circles"]
}
```
> 💡 `theme_colors`가 있으면 동적 테마가 우선 적용되며, 배경 패턴과 아이콘은 설정된 프리셋에 따라 CSS로 자동 스위칭됩니다. 없으면 기존 고정 테마(`theme: "tech_blue"`)를 사용합니다.


### 문장 압축 및 무손실 원칙
- **제목**: 20자 이내 우선
- **항목 (Bullet)**: 슬라이드당 최대 3개, 각 20자 이내 (글씨 크기 확대로 인해 엄격 제한)
- **텍스트 강조 (`<strong>`)**: 각 항목이나 본문 내에서 시각적 환기를 위해 청중이 기억해야 할 핵심 키워드/명사구 1~2개는 반드시 `<strong>` 태그로 래핑하여 생성합니다. (예: `일주일 이상 걸리던 <strong>나이스 출결 취합 작업</strong>을 단 하루 만에 완료`)
- **BOTTOM_TAKEAWAY**: 청중이 반드시 기억해야 할 핵심 한 줄을 슬라이드 하단에 배치 (선택 속성, 모든 레이아웃에서 사용 가능)
- **무손실 원칙**: 슬라이드 화면에 담지 못한 원문의 긴 문장, 부연 설명, 출처는 무조건 `SPEAKER_NOTES` 항목으로 밀어넣어 정보 유실을 방지합니다.

### 아이콘 불릿 (Icon Bullet)
`BULLET_ITEMS`에 문자열 대신 `{"icon": "💡", "text": "내용"}` 객체를 넣으면, 기본 점(•) 대신 이모지 아이콘이 표시됩니다.
```json
"BULLET_ITEMS": [
    {"icon": "🎯", "text": "1단계: 목표 설정"},
    {"icon": "🔍", "text": "2단계: 현황 분석"},
    {"icon": "🚀", "text": "3단계: 실행 및 평가"}
]
```

### 정보 유형별 레이아웃 선택 가이드
단순 글머리기호(bullet) 나열을 **최소화**하고, 정보의 성격에 맞는 전용 레이아웃을 사용합니다.

| 정보 성격 | 권장 레이아웃 | 예시 |
|-----------|--------------|------|
| 순서/절차 | `roadmap` | 학교폭력 처리 4단계 |
| 시간 흐름/상태 변화 | `timeline` | 1분 이내 → 2~3분 → 5분 이상 |
| 비교/대조 | `comparison`, `vs_ox` | 전통 교육 vs AI 교육 |
| 분류/유형 | `matrix` | 에듀테크 4분면 선택 기준 |
| 핵심 수치 | `stats` | 만족도 95%, 참여율 87% |
| 명언/인용 | `quote` | 전문가 의견 |

### 순서형 레이아웃 항목 수 규칙
- `roadmap`: 절차/단계가 명확한 경우 3~5개를 허용하고, 기본은 4개를 권장합니다. 2개만 있으면 `comparison` 또는 `vs_ox`를 우선 검토합니다.
- `timeline`: 시간 흐름·상태 변화는 3~6개를 허용합니다. 4개 이하는 가로 rail 구조, 5개 이상은 compact 구조로 렌더링됩니다.
- 6개를 초과하는 절차나 시간 흐름은 한 장에 밀어 넣지 말고 여러 장으로 분할합니다.

### 🔄 스텝퍼(Stepper) 레이아웃의 슬라이드 개수 1:1 동기화 원칙
`hands_on`, `tutorial` 등 진행 과정(Stepper)을 보여주는 레이아웃을 사용할 때는 **내용의 전체 단계 수와 동일한 개수의 슬라이드(JSON 객체)를 반드시 생성**해야 합니다.
- **예시**: 실습이 5단계로 구성되어 있다면, `slide_plan.json` 내에 해당 레이아웃을 가진 슬라이드 객체를 정확히 5개 복제하여 생성해야 합니다.
- 각 슬라이드는 하나의 단계를 설명하며, 슬라이드가 넘어갈 때마다 스텝퍼의 활성화(`"state": "active"`) 위치가 한 칸씩 이동하도록 `STEPPER_ITEMS` 상태를 조절해야 합니다.
- 단계가 누락되거나 하나의 슬라이드에 여러 단계를 구겨 넣지 마세요.

### 이미지 vs 도식 판정 기준
- **이미지 생성**: 실존 대상, 감성적 표지, 구체적 사례, 비전. 사용 가능한 이미지 생성 도구를 쓰며, 스타일은 **플랫 디자인, 파스텔 톤, 배경 투명 컷아웃(cut-out)** 형태를 기본으로 합니다.
- **도식 생성 (Mermaid)**: 흐름(flowchart), 비교, 구조(block), 수치 비율(pie), 데이터 중심 표

### slide_plan.json 스키마 예시
```json
{
  "meta": {
    "title": "AI 교육 트렌드 2026",
    "theme_colors": {
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
      "decorations": ["corner_accent", "circles"]
    }
  },
  "slides": [
    {
      "type": "hero",
      "BADGE": "2026 교원연수",
      "TITLE": "교실 속 AI, 어디까지 왔나?",
      "SUBTITLE": "현장 교사가 체감하는 진짜 AI 리터러시",
      "PRESENTER": "김목동 선생님",
      "SPEAKER_NOTES": "선생님들 반갑습니다. 오늘은 AI가 교실에..."
    },
    {
      "type": "bullet",
      "SECTION_HEADER": "Part 1. AI 리터러시",
      "TITLE": "AI 리터러시 3단계",
      "BULLET_ITEMS": [
        {"icon": "🎯", "text": "AI 도구의 이해와 조작"},
        {"icon": "🔍", "text": "수업 적용과 윤리적 판단"},
        {"icon": "🚀", "text": "학생 주도형 AI 프로젝트 설계"}
      ],
      "BOTTOM_TAKEAWAY": "AI 리터러시는 기술이 아닌 '역량'입니다",
      "SPEAKER_NOTES": "본문에서 생략된 자세한 설명들... (30자 넘는 내용)"
    },
    {
      "type": "vs_ox",
      "TITLE": "효과적인 AI 활용법 O/X",
      "O_MARKER": "✅",
      "O_TITLE": "이렇게 하세요",
      "O_ITEMS": [
        {"text": "학생이 직접 질문을 설계"},
        {"text": "AI 결과를 비판적으로 검증"}
      ],
      "X_MARKER": "⛔",
      "X_TITLE": "이것은 피하세요",
      "X_ITEMS": [
        {"text": "AI 답변을 그대로 복사"},
        {"text": "교사 없이 AI에만 의존"}
      ],
      "SPEAKER_NOTES": "O/X 비교 설명..."
    },
    {
      "type": "matrix",
      "TITLE": "에듀테크 도구 선택 매트릭스",
      "MATRIX_ITEMS": [
        {"icon": "📝", "label": "퀴즈/평가", "desc": "카훗, 구글 폼"},
        {"icon": "🎨", "label": "창작/제작", "desc": "캔바, 클립챔프"},
        {"icon": "🤝", "label": "협업/소통", "desc": "패들렛, 잼보드"},
        {"icon": "📊", "label": "데이터/분석", "desc": "스프레드시트, AI"}
      ],
      "SPEAKER_NOTES": "매트릭스 설명..."
    },
    {
      "type": "roadmap",
      "TITLE": "AI 수업 설계 로드맵",
      "ROADMAP_ITEMS": [
        {"label": "목표 설정", "desc": "성취기준 분석"},
        {"label": "도구 선택", "desc": "적합한 AI 도구"},
        {"label": "수업 설계", "desc": "활동 구성"},
        {"label": "실행·평가", "desc": "피드백 반영"}
      ],
      "BOTTOM_TAKEAWAY": "좋은 수업은 기술이 아닌 설계에서 시작됩니다",
      "SPEAKER_NOTES": "로드맵 설명..."
    },
    {
      "type": "timeline",
      "TITLE": "학습 흐름 타임라인",
      "TIMELINE_ITEMS": [
        {"date": "도입", "title": "맥락 열기", "desc": "핵심 질문 제시"},
        {"date": "전개", "title": "활동 수행", "desc": "자료 분석과 토의"},
        {"date": "정리", "title": "전이 확인", "desc": "실천 과제 연결"}
      ],
      "SPEAKER_NOTES": "시간 흐름이나 상태 변화 설명..."
    },
    {
      "type": "stats",
      "TITLE": "핵심 수치 하이라이트",
      "STAT_ITEMS": [
        {"value": "95%", "label": "교사 만족도"},
        {"value": "12만명", "label": "누적 참여 학생 수"}
      ],
      "SPEAKER_NOTES": "통계 레이아웃은 STAT_ITEMS 배열(value, label)을 반드시 사용합니다."
    },
    {
      "type": "quiz",
      "TITLE": "다음 중 올바른 행동은?",
      "QUESTION": "모르는 사람이 무료 도토리를 준다면?",
      "QUIZ_OPTIONS": [
        {"text": "고맙다고 하고 받는다"},
        {"text": "무조건 의심하고 피한다"}
      ],
      "ANSWER_INDEX": 1,
      "SPEAKER_NOTES": "퀴즈 레이아웃은 선택지 출력을 위해 QUIZ_OPTIONS 배열을 반드시 사용합니다."
    },
    {
      "type": "tutorial",
      "TITLE": "나이스 출결 메뉴 찾기",
      "STEP_NUMBER": "2",
      "STEPPER_ITEMS": [
        {"label": "로그인", "state": "completed"},
        {"label": "출결 메뉴", "state": "active"},
        {"label": "학생 선택", "state": "inactive"},
        {"label": "저장", "state": "inactive"}
      ],
      "BULLET_ITEMS": [
        "상단 메뉴에서 [학적] 클릭",
        "좌측 트리에서 [출결관리] 선택",
        "[출결현황] 탭을 클릭합니다"
      ],
      "TIP": "Ctrl+F로 메뉴를 검색할 수도 있습니다",
      "IMAGE_SRC": "images/neis_menu.png",
      "SPEAKER_NOTES": "나이스 상단 메뉴 중 학적을 먼저 클릭하고..."
    }
  ]
}
```

### 공통 선택 속성 (모든 레이아웃에서 사용 가능)
- `BOTTOM_TAKEAWAY`: 슬라이드 하단에 그라데이션 띠로 표시되는 핵심 요약 한 줄
- `SECTION_HEADER`: 슬라이드 좌상단에 작게 표시되는 현재 섹션명 (네비게이션 용)

*지원 레이아웃*: `hero`, `title`, `split`, `text_image`, `bullet`, `comparison`, `image_comparison`, `timeline`, `quiz`, `quote`, `diagram`, `stats`, `summary`, `closing`, `tutorial`, `hands_on`, `fullbleed`, `matrix`, `vs_ox`, `roadmap`, `activity`, `activity_instruction`, `video_hook`, `video_link_card`

### 📚 레이아웃별 필수/선택 변수명 사전 (Schema Dictionary)
AI가 `slide_plan.json`을 생성할 때 템플릿과 파이썬 스크립트에서 정확히 인식할 수 있도록, **반드시 아래 표에 명시된 변수명(대문자)만을 사용**해야 합니다. (임의의 변수명 지어내기 엄금)

**렌더러 우선 원칙**: 입력 스키마의 기준은 `scripts/build_html.py`가 읽는 키입니다. `OX_REVEAL_ITEMS`, `MATCHING_REVEAL_ITEMS`, `TABLE_REVEAL_HTML`처럼 렌더러가 생성하는 HTML 치환용 키를 `slide_plan.json` 입력키로 쓰지 마세요.

| 항목 | 입력 내부 키 | 사용하지 말 것 |
|---|---|---|
| `ROADMAP_ITEMS` | `label`, `desc` | `step`, `title`, `body` |
| `MATRIX_ITEMS` | `icon`, `label`, `desc` | `body` |
| `TIMELINE_ITEMS` | `date`, `title`, `desc` | `body` |
| `STAT_ITEMS` | `value`, `label`, `percentage` | `number`, `text` |
| `QUIZ_OPTIONS` | `text` + `ANSWER_INDEX` | `correct`만 의존 |
| `O_ITEMS`, `X_ITEMS` | 문자열 또는 `{ "text": "..." }` | `{ "body": "..." }` |
| `activity` | `ACTIVITY_REF` | `WORKSHEET_BLOCK`, `ITEMS`, `PAIRS`, `HEADERS`, `ROWS` 직접 중복 |

| 레이아웃 타입 | 용도 및 설명 | 필수 변수 | 선택(옵션) 변수 |
|---|---|---|---|
| `hero` | 표지, 대제목 | `TITLE` | `SUBTITLE`, `BADGE`, `PRESENTER`, `SPEAKER_NOTES` |
| `title` | 섹션 표지 | `TITLE` | `SUBTITLE`, `SPEAKER_NOTES` |
| `split` | 좌측 텍스트, 우측 이미지 | `TITLE`, `BODY`, `IMAGE_SRC` | `SPEAKER_NOTES` |
| `text_image` | 본문과 이미지 | `TITLE`, `CONTENT`, `IMAGE_SRC` | `SPEAKER_NOTES` |
| `bullet` | 일반 글머리기호 목록 | `TITLE`, `BULLET_ITEMS` (배열) | `BOTTOM_TAKEAWAY`, `SPEAKER_NOTES` |
| `comparison` | 좌우 대칭 비교 | `TITLE`, `LEFT_TITLE`, `LEFT_ITEMS`, `RIGHT_TITLE`, `RIGHT_ITEMS` | `SPEAKER_NOTES` |
| `image_comparison` | Before & After 이미지 2장 비교 | `TITLE`, `LEFT_IMAGE_SRC`, `LEFT_DESC`, `RIGHT_IMAGE_SRC`, `RIGHT_DESC` | `BOTTOM_TAKEAWAY`, `SPEAKER_NOTES` |
| `timeline` | 시간 흐름/상태 변화 | `TITLE`, `TIMELINE_ITEMS` (`date`, `title`, `desc`) | `BOTTOM_TAKEAWAY`, `SPEAKER_NOTES` |
| `quiz` | 객관식 퀴즈 | `TITLE`, `QUESTION`, `QUIZ_OPTIONS` (text) | `ANSWER_INDEX`, `SPEAKER_NOTES` |
| `quote` | 명언, 핵심 인용구 | `QUOTE_TEXT` | `QUOTE_SOURCE`, `SPEAKER_NOTES` |
| `diagram` | Mermaid 등 도식 | `TITLE`, `DIAGRAM_SRC` | `DIAGRAM_CAPTION`, `SPEAKER_NOTES` |
| `stats` | 핵심 통계 수치 하이라이트 | `TITLE`, `STAT_ITEMS` (value, label) | `SPEAKER_NOTES` |
| `summary` | 핵심 요약 리스트 | `TITLE`, `SUMMARY_ITEMS` (`title`, `desc` 권장. 문자열도 허용) | `BOTTOM_TAKEAWAY`, `SPEAKER_NOTES` |
| `closing` | 마무리 및 행동 유도 | `TITLE`, `MESSAGE` | `CTA`, `BULLET_ITEMS`, `SPEAKER_NOTES` |
| `tutorial` | UI 스텝퍼 포함 튜토리얼 | `TITLE`, `STEP_NUMBER`, `STEPPER_ITEMS` (label, state) | `BULLET_ITEMS`, `TIP`, `WARNING`, `IMAGE_SRC`, `SPEAKER_NOTES` |
| `hands_on` | 실습 지시 및 예상 결과 | `TITLE`, `STEPPER_ITEMS` (label, state) | `BULLET_ITEMS`, `TIP`, `DURATION`, `IMAGE_SRC`, `RESULT_TEXT`, `SPEAKER_NOTES` |
| `fullbleed` | 전체 화면 이미지 배경 | `TITLE`, `IMAGE_SRC` | `SUBTITLE`, `STEPPER_ITEMS`, `SPEAKER_NOTES` |
| `matrix` | 2x2 아이콘 매트릭스 | `TITLE`, `MATRIX_ITEMS` (icon, label, desc) | `SPEAKER_NOTES` |
| `vs_ox` | 2단 행동/가치 대비 가이드 | `TITLE`, `O_TITLE`, `O_ITEMS` (marker, text), `X_TITLE`, `X_ITEMS` | `O_MARKER`, `X_MARKER`, `BOTTOM_TAKEAWAY`, `SPEAKER_NOTES` |
| `roadmap` | 3~5단계 가로 로드맵 카드 | `TITLE`, `ROADMAP_ITEMS` (label, desc) | `SUBTITLE`, `BOTTOM_TAKEAWAY`, `SPEAKER_NOTES` |
| `activity` | 활동지 문항 표시 후 같은 화면에서 정답 공개 | `ACTIVITY_REF` | `TITLE`, `BOTTOM_TAKEAWAY`, `SPEAKER_NOTES` |
| `activity_instruction` | 학습지 활동 안내 | `TITLE`, `INSTRUCTION` | `WORKSHEET_REF`, `TIMER_MINUTES`, `THINK_QUESTION`, `SPEAKER_NOTES` |
| `video_hook` | 슬라이드 안에서 바로 재생하는 영상 | `TITLE`, `EMBED_URL` | `PURPOSE`, `STUDENT_TASK`, `SPEAKER_NOTES` |
| `video_link_card` | YouTube 새 창으로 여는 영상 카드 | `TITLE`, `WATCH_URL` | `THUMBNAIL_URL`, `PURPOSE`, `STUDENT_TASK`, `SPEAKER_NOTES` |

*(참고: 모든 레이아웃 공통으로 `SECTION_HEADER`와 `BOTTOM_TAKEAWAY`는 원할 경우 선택 변수로 추가 가능합니다.)*

### ⚠️ 다중 슬라이드 구성 강제 규칙 (흐름형/퀴즈형 레이아웃)
- **흐름형 (`tutorial`, `hands_on`)**: 상단 스텝퍼(`STEPPER_ITEMS`)나 단계별 진행이 포함되는 레이아웃을 적용할 때는, **반드시 전체 스텝(예: 1단계, 2단계, 3단계 등)에 해당하는 독립적인 슬라이드들을 순차적으로 연속 분할 생성**해야 합니다. 단 한 장의 슬라이드만 덩그러니 배치하여 흐름을 끊는 설계를 엄격히 금지합니다.
- **퀴즈형 (`quiz`, `vs_ox`)**: 내용상 복수의 퀴즈 문제가 필요하거나 학습 내용을 복습하기 위한 여러 문제가 제공되어야 하는 경우, 1장으로 뭉뚱그려 표시하지 말고 **문제별로 독립적인 슬라이드(예: 퀴즈 1, 퀴즈 2, 퀴즈 3)를 여러 장 연속해서 분할 생성**하세요.

> 💡 `split` 레이아웃: 화면을 좌우로 나누어 텍스트(BODY)와 이미지(IMAGE_SRC)를 나란히 배치합니다. 이미지가 있는 내용 설명 슬라이드에 적합합니다.

---

## 모듈 4: 에셋 생성 (도식 및 이미지)

`slide_plan.json`에 `diagram`이나 `text_image` 타입이 포함되어 있다면 에셋을 생성합니다.

1. **도식 (Mermaid)**
   - `scripts/render_mermaid.py`를 사용해 SVG 생성
   - `DIAGRAM_SRC` 속성에 `diagrams/파일명.svg` 상대 경로 기록
2. **이미지 (AI)**
   - 사용 가능한 이미지 생성 도구 사용
   - `IMAGE_SRC` 속성에 `images/파일명.png` 상대 경로 기록

---

## 모듈 5: HTML 렌더링 및 검수

1. 에이전트가 `scripts/build_html.py` 스크립트를 실행하여 슬라이드를 빌드합니다.
   ```bash
   python "{스킬폴더}/scripts/build_html.py" "slide_plan.json" "output/index.html"
   ```
2. **[실시간 저장/검수용 로컬 서버 자동 가동]** 빌드 완료 직후, 에이전트는 로컬 8000번 포트에서 개발 서버가 돌고 있는지 확인합니다. 만약 켜져 있지 않다면, 사용자가 순서 변경/삭제의 실시간 로컬 저장을 원활히 쓸 수 있도록 아래 명령을 **백그라운드 비동기 태스크**로 즉시 실행하여 서버를 가동시켜 둡니다.
   ```bash
   # 프로젝트 폴더 내부(CWD) 기준 실행
   python "{스킬폴더}/scripts/dev_server.py"
   ```
3. 에러가 발생하면 JSON 문법을 고치고 다시 실행합니다.
4. 생성된 `output/index.html`을 검토한 후, 사용자에게 실시간 로컬 싱크 프리뷰 링크(`http://localhost:8000`)를 최종 안내합니다.
    - `capture_png.py`는 `captured_images/qa-report.json`을 생성하며 화면에 보이는 모든 텍스트를 검사합니다. 편집 필드가 아닌 고정 라벨도 포함하며, `overflow:hidden`인 상위 박스에 의한 잘림, off-slide, 루트 overflow, 18px 미만 화면 텍스트, 학습지 잘림이 있으면 실패합니다.
    - 스킬 구조를 수정한 뒤에는 `python "{스킬폴더}/scripts/test_layout_regression.py" "{임시출력폴더}"`로 고정 테마 7종과 동적 폰트 5종의 전체 레이아웃 회귀를 실행합니다. 특정 변형만 재현할 때는 `--variant cute_note`처럼 지정합니다.
    - `file://.../output/index.html`은 보기 전용으로만 사용하고, 저장/순서 변경이 필요한 검수에는 로컬 서버 URL을 사용합니다.
   - 8000번 포트가 이미 사용 중이면 기존 서버의 프로젝트 CWD를 확인하거나 다른 포트를 사용합니다.

---

## 모듈 6: 최종 파일 추출 (통이미지 PPTX)

사용자에게 배포용 납품 파일인 PPTX를 생성합니다.
HTML 프리뷰의 완벽한 레이아웃과 렌더링(반투명 형광펜, 오토핏 등)을 깨짐 없이 보존하기 위해, 슬라이드를 이미지로 캡처한 뒤 통이미지 기반의 PPTX를 생성합니다. (세부 수정은 HTML/JSON 에디터 환경에서 수행하는 것을 원칙으로 합니다.)

```bash
# 1. HTML을 고해상도 PNG 이미지로 캡처
python "{스킬폴더}/scripts/capture_png.py" "output/index.html" "output/captures"

# 2. 캡처된 이미지들을 와이드 PPTX로 묶어서 생성
python "{스킬폴더}/scripts/export_image_pptx.py" "output/captures" "output/presentation.pptx"
```

완성되면 사용자에게 HTML 프리뷰 링크와 PPTX 파일 경로를 안내하며 작업을 마칩니다.

---

## 🔧 수정 모드 (Edit Mode) 및 아키텍처 경계 가이드 (★ 매우 중요)

사용자가 내용 수정을 요청할 경우, 에이전트는 무작정 공통 스킬 코드를 수정하지 않고 아래 **[Core vs Project Isolation] 판단 기준**에 따라 전략적으로 작업을 수행합니다.

### 1. Core 업그레이드 대상 (공통 스킬 코드 직접 수정)
* **판단 기준**:
  - 슬라이드 전반의 **범용 인터랙션 및 동적 기능** (예: 대시보드 게이지 클릭 모션, 퀴즈 클릭 피드백).
  - 템플릿 마크업 개선 및 **하위 호환성/방어적 렌더링** (예: 이미지 경로가 없을 때 레이아웃이 깨지지 않도록 if/else 예외 처리).
  - 테마 전용 스타일 개선 (예: `cute_note` 테마 내에서의 겹침 문제 해결을 위한 padding/margin 조절).
* **작업 요령**: 
  - 공통 스킬 폴더 내의 `templates`나 `scripts` 파일을 직접 수정합니다.
  - 수정 완료 즉시 **글로벌 룰**에 따라 옵시디언 금고 및 시스템 config 스킬 폴더로 **전체 동기화(덮어쓰기)**를 진행하여 다음 프로젝트에서도 이 기능이 보존되도록 합니다.


### 3. 새로운 레이아웃/블록 추가 시 텍스트 편집 연동 규칙 (필수)
* **상황**: 새로운 `block_type`이나 인터랙티브 슬라이드 레이아웃을 `build_html.py`의 `render_worksheet_block` 등에 추가할 때.
* **작업 요령 (에디터 연동 유지)**: 
  - 텍스트가 표시되는 모든 HTML 요소(표 셀, 빈칸, 설명글 등)에는 절대로 `contenteditable="true"` 속성을 직접 하드코딩하지 마세요. (이렇게 하면 우측 텍스트 에디터 패널과의 데이터 연결이 끊어져 점선 박스나 글자 크기 조절이 작동하지 않습니다.)
  - 반드시 파이썬 스크립트 상에서 **`editable_attrs(f"{prefix}.경로")`** 함수를 호출하여 태그에 주입해야 합니다.
  - 예시: `<h2{editable_attrs(f"{prefix}.title")}>{title}</h2>`
  - 이렇게 처리해야 "텍스트 직접편집" 탭에 진입했을 때만 점선 박스가 켜지고, 클릭 시 에디터 패널과 완벽히 동기화됩니다.

### 2. Project Isolation 대상 (개별 프로젝트 폴더 내 격리)
* **판단 기준**:
  - 특정 프로젝트에서만 유효한 **일회성 데이터 연산 및 전처리** (예: 특정 CSV/나이스 출결 데이터를 슬라이드로 변환하는 2차 가공 스크립트).
  - 특정 슬라이드 1개의 국소적인 스타일 변경 (예: "12번 슬라이드 글머리 글씨만 조금 키워줘").
* **작업 요령**:
  - 공통 스킬의 원본 소스 코드(`build_html.py` 등)는 **절대 오염시키지 말고 순수하게 보존**합니다.
  - 개별 텍스트 글자 크기 등은 `slide_plan.json` 내의 텍스트에 직접 인라인 스타일(`<span style="...">`)로 묻어두어 격리합니다.
  - 복잡한 로컬 전처리는 프로젝트 폴더 내에 전용 파이썬 스크립트(예: `custom_helper.py`)를 따로 작성하여 격리 실행합니다.

#바이브코딩 #프레젠테이션 #슬라이드 #Antigravity #교육 #SSOT


## 🎨 CSS 및 레이아웃 전역 규칙 (CSS & Layout Global Rules)

- **한국어 텍스트 줄바꿈 (Word Breaking)**: 모든 레이아웃에서 한글 텍스트는 반드시 단어 단위(Word-level)로 줄바꿈 되어야 합니다. 전역 컨테이너(.reveal 등)에 word-break: keep-all;을 선언하여 사용하고, 레이아웃별로 word-break: keep-all;을 사용하는 것을 엄격히 금지합니다. 추후 새로운 레이아웃을 추가할 때도 이 전역 규칙이 유지되어야 합니다.
