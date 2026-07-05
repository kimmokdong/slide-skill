#!/usr/bin/env python3
"""수업형 슬라이드+활동지 프로젝트 초기 파일을 생성합니다.

사용법:
    python init_lesson_project.py --answers answers.json
    python init_lesson_project.py
"""

import argparse
import datetime as dt
import json
import re
from pathlib import Path


DEFAULT_THEME_COLORS = {
    "bg": "#F7FAF6",
    "bg_secondary": "#E8F1EA",
    "text": "#1F2933",
    "text_secondary": "#52616B",
    "accent": "#2F855A",
    "accent_secondary": "#3B82F6",
    "card_style_preset": "business_clean",
    "icon_preset": "business",
    "font_preset": "friendly",
    "highlight_style": "friendly",
    "takeaway_style": "friendly",
    "motion_preset": "friendly",
    "image_frame_preset": "business",
    "bg_pattern_style": "grid",
    "decorations": ["corner_accent"],
}


def ask(prompt, default=""):
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def slugify(text):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return slug or "lesson_project"


def yaml_scalar(value):
    value = "" if value is None else str(value)
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_yaml(path, data):
    lines = []
    for key, value in data.items():
        lines.append(f"{key}: {yaml_scalar(value)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def default_ox_items(topic):
    return [
        {
            "statement": f"{topic}에서는 먼저 내 생각을 말해 보는 것이 중요하다.",
            "answer": "O",
            "explanation": "수업 활동은 학생의 첫 생각을 확인하는 데서 출발합니다.",
        },
        {
            "statement": f"{topic}에 대해 친구의 의견은 들을 필요가 없다.",
            "answer": "X",
            "explanation": "서로 다른 생각을 비교해야 개념이 더 분명해집니다.",
        },
        {
            "statement": f"{topic} 학습 후에는 배운 내용을 정리해야 한다.",
            "answer": "O",
            "explanation": "정리는 다음 활동이나 평가로 이어지는 기준점이 됩니다.",
        },
    ]


def collect_answers():
    topic = ask("수업 주제", "가짜뉴스를 구별하는 방법")
    return {
        "project_name": ask("프로젝트 영문 이름", slugify(topic)),
        "raw_script": ask("원문/메모", f"주제: {topic}"),
        "audience_level": ask("청중/학년", "초등 5학년"),
        "grade": ask("학년", "초등 5학년"),
        "subject": ask("교과", "국어"),
        "topic": topic,
        "duration_minutes": int(ask("수업 시간(분)", "40")),
        "slide_count": int(ask("슬라이드 수", "5")),
        "tone": ask("톤", "친근"),
        "category": ask("카테고리", "교과교육"),
        "presentation_mode": ask("발표 환경", "대면"),
        "theme_preference": ask("테마", "AI 알아서 맞춤"),
        "goal": ask("학습 목표", f"{topic}을 설명하고 적용할 수 있다."),
        "big_question": ask("큰 질문", "이 정보는 믿어도 될까?"),
        "activity_title": ask("활동 제목", f"{topic} OX 퀴즈"),
        "work_time_minutes": int(ask("활동 시간(분)", "2")),
    }


def load_answers(path):
    if not path:
        return collect_answers()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_plan(answers):
    topic = answers.get("topic", "수업 주제")
    title = answers.get("title") or topic
    goal = answers.get("goal", f"{topic}을 설명하고 적용할 수 있다.")
    big_question = answers.get("big_question", "무엇을 확인해야 할까?")
    activity_title = answers.get("activity_title", f"{topic} OX 퀴즈")
    work_time = int(answers.get("work_time_minutes", 2) or 2)
    ox_items = answers.get("ox_items") or default_ox_items(topic)

    worksheet_block = {
        "block_type": "ox_check",
        "title": "활동 1. OX로 확인하기",
        "instruction": "맞으면 O, 틀리면 X에 표시하세요.",
        "items": ox_items,
    }

    return {
        "meta": {
            "title": title,
            "theme_colors": answers.get("theme_colors", DEFAULT_THEME_COLORS),
        },
        "content_blueprint": {
            "lesson_info": {
                "mode": "elementary_lesson",
                "grade": answers.get("grade", answers.get("audience_level", "")),
                "subject": answers.get("subject", ""),
                "topic": topic,
                "duration_minutes": int(answers.get("duration_minutes", 40) or 40),
            },
            "goal": goal,
            "big_question": big_question,
            "flow": [
                {
                    "stage": "도입",
                    "purpose": "수업 주제와 큰 질문을 확인한다.",
                    "teacher_action": "사례나 질문을 제시한다.",
                    "student_action": "첫 생각을 말한다.",
                    "slide_role": "도입 질문 제시",
                    "worksheet_role": "첫 생각 쓰기",
                },
                {
                    "stage": "활동 1",
                    "activity_id": "activity_1",
                    "purpose": "핵심 개념을 OX로 확인한다.",
                    "teacher_action": "학습지 풀이 후 화면으로 정답을 확인한다.",
                    "student_action": "OX 문제를 풀고 정답 확인에 참여한다.",
                    "worksheet_block_type": "ox_check",
                    "slide_review_layout": "ox_reveal",
                },
            ],
        },
        "activity_packages": [
            {
                "activity_package_id": "activity_1",
                "title": activity_title,
                "student_task": "학습지 1번 OX 문제를 푼다.",
                "work_time_minutes": work_time,
                "worksheet_block": worksheet_block,
                "teacher_prompt": [
                    "정답을 바로 보여주지 말고 학생이 먼저 O/X로 대답하게 한다.",
                    "학생 답을 들은 뒤 클릭하여 정답을 하나씩 공개한다.",
                ],
            }
        ],
        "pages": [
            {
                "page_type": "slide",
                "size": "16:9",
                "layout": "hero",
                "BADGE": answers.get("subject", "수업"),
                "TITLE": title,
                "SUBTITLE": big_question,
            },
            {
                "page_type": "slide",
                "size": "16:9",
                "layout": "bullet",
                "TITLE": "오늘의 목표",
                "BULLET_ITEMS": [
                    {"icon": "1", "text": goal},
                    {"icon": "2", "text": "학습지 활동으로 내 생각을 확인합니다."},
                    {"icon": "3", "text": "정답과 이유를 함께 이야기합니다."},
                ],
            },
            {
                "page_type": "slide",
                "size": "16:9",
                "layout": "activity_instruction",
                "TITLE": f"활동 1. {activity_title}",
                "WORKSHEET_REF": "학습지 1번",
                "INSTRUCTION": "OX 문제를 풀어 봅시다.",
                "TIMER_MINUTES": work_time,
                "THINK_QUESTION": big_question,
            },
            {
                "page_type": "slide",
                "size": "16:9",
                "layout": "ox_reveal",
                "TITLE": "활동 1 정답 확인",
                "ITEMS": ox_items,
            },
            {
                "page_type": "slide",
                "size": "16:9",
                "layout": "closing",
                "TITLE": "정리하기",
                "MESSAGE": "오늘 배운 내용을 한 문장으로 정리해 봅시다.",
                "CTA": big_question,
            },
            {
                "page_type": "worksheet",
                "size": "A4",
                "title": title,
                "blocks": [
                    {
                        "block_type": "short_answer",
                        "title": "생각 열기",
                        "prompt": big_question,
                        "answer_lines": 2,
                    },
                    worksheet_block,
                ],
            },
            {
                "page_type": "answer_key",
                "size": "A4",
                "title": f"{title} 정답지",
                "blocks": [worksheet_block],
            },
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--answers", help="질문 답변 JSON 파일")
    parser.add_argument("--project-dir", help="생성할 프로젝트 폴더")
    args = parser.parse_args()

    answers = load_answers(args.answers)
    date_prefix = dt.datetime.now().strftime("%y%m%d")
    project_name = args.project_dir or f"{date_prefix}_{slugify(answers.get('project_name') or answers.get('topic', 'lesson_project'))}"
    project_dir = Path(project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    raw_script = answers.get("raw_script") or f"주제: {answers.get('topic', '')}"
    (project_dir / "raw_script.md").write_text(raw_script.strip() + "\n", encoding="utf-8")

    write_yaml(project_dir / "slide_context.yaml", {
        "audience_level": answers.get("audience_level", answers.get("grade", "")),
        "lecture_duration_min": answers.get("duration_minutes", 40),
        "slide_count": answers.get("slide_count", 5),
        "tone": answers.get("tone", "친근"),
        "category": answers.get("category", "교과교육"),
        "presentation_mode": answers.get("presentation_mode", "대면"),
        "theme_preference": answers.get("theme_preference", "AI 알아서 맞춤"),
        "artifact_mode": "slides_with_worksheet",
    })

    plan = build_plan(answers)
    (project_dir / "slide_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"[SUCCESS] 프로젝트 초기 파일 생성: {project_dir}")
    print(f" - {project_dir / 'raw_script.md'}")
    print(f" - {project_dir / 'slide_context.yaml'}")
    print(f" - {project_dir / 'slide_plan.json'}")


if __name__ == "__main__":
    main()
