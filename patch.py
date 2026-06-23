import re

with open('.agents/skills/text-to-slide-architect/templates/includes/scripts/theme_editor.js', 'r', encoding='utf-8') as f:
    js = f.read()

js = re.sub(
    r'<<<<<<< HEAD\n.*?=======\n(.*?)\n>>>>>>> origin/main',
    r'\1',
    js,
    flags=re.DOTALL
)

with open('.agents/skills/text-to-slide-architect/templates/includes/scripts/theme_editor.js', 'w', encoding='utf-8') as f:
    f.write(js)

with open('.agents/skills/text-to-slide-architect/scripts/dev_server.py', 'r', encoding='utf-8') as f:
    py = f.read()

py = re.sub(
    r'<<<<<<< HEAD\nimport uuid\nfrom pathlib import Path\n=======\nimport copy\nimport re\nimport shutil\nimport time\n>>>>>>> origin/main\n',
    'import copy\nimport re\nimport shutil\nimport time\nimport uuid\nfrom pathlib import Path\n',
    py
)

t_path = """        if clean_path == "/":
            return str(Path.cwd() / "output" / "index.html")

        if clean_path.startswith("/output/"):
            rel_path = clean_path[8:]
            return safe_child_path(Path.cwd() / "output", rel_path)

        for asset_dir in ["images", "diagrams", "includes", "audio"]:
            if clean_path.startswith(f"/{asset_dir}/"):
                return safe_child_path(Path.cwd() / "output", clean_path.lstrip("/"))"""

py = re.sub(
    r'<<<<<<< HEAD\n        if clean_path == "/":.*?>>>>>>> origin/main\n',
    t_path + '\n',
    py,
    flags=re.DOTALL
)

do_post_resolved = '''            self.require_local_request()

            if parsed.path == "/api/save-order":
                self.handle_save_order()
            elif parsed.path == "/api/upload-image":
                self.handle_upload_image()
            elif parsed.path == "/api/save-theme":
                req_json = self.read_json_payload()
                theme_colors = req_json.get('theme_colors')
                plan = load_plan(get_plan_path())
                plan.setdefault('meta', {})['theme_colors'] = theme_colors
                save_plan_atomic(get_plan_path(), plan)
                rebuild = rebuild_outputs()
                self.send_json_response(200, {"status": "success", "message": "테마 저장 완료", "rebuild": rebuild})
            elif parsed.path == "/api/save-text-edits":
                req_json = self.read_json_payload()
                plan = load_plan(get_plan_path())
                try:
                    apply_text_edits(plan, req_json.get('edits', []), req_json.get('style_overrides', []))
                    save_plan_atomic(get_plan_path(), plan)
                    rebuild = rebuild_outputs()
                    self.send_json_response(200, {"status": "success", "message": "텍스트 직접 편집 저장 완료", "rebuild": rebuild})
                except ValueError as e:
                    raise ApiError(400, str(e))
            else:
                raise ApiError(404, "API endpoint was not found.")
        except ApiError as exc:
            self.send_error_response(exc.status_code, exc.message)
        except Exception as exc:
            print(f"[ERROR] Request failed: {exc}")
            self.send_error_response(500, f"Server error: {exc}")

    def handle_save_order(self):
        payload = self.read_json_payload()
        indices = payload.get("indices", [])
        if not isinstance(indices, list):
            raise ApiError(400, "indices must be an array.")

        plan_path = get_plan_path()
        plan = load_plan(plan_path)
        original_slides = plan.get("slides", [])
        if not isinstance(original_slides, list):
            raise ApiError(400, "slide_plan.json must contain a slides array.")

        new_slides = []
        for idx in indices:
            if isinstance(idx, bool) or not isinstance(idx, int):
                raise ApiError(400, "indices must contain integers only.")
            if idx < 0 or idx >= len(original_slides):
                raise ApiError(400, f"Invalid slide index: {idx}")
            new_slides.append(original_slides[idx])

        backup_path = backup_plan(plan_path)
        plan["slides"] = new_slides
        save_plan_atomic(plan_path, plan)
        rebuild = rebuild_outputs()

        self.send_json_response(
            200,
            {
                "status": "success",
                "message": "Slide order saved and outputs rebuilt.",
                "backup": backup_path.name,
                "rebuild": rebuild,
            },
        )

    def handle_upload_image(self):
        payload = self.read_json_payload()

        slide_index = payload.get("slide_index")
        target_key = payload.get("target_key")

        if isinstance(slide_index, bool) or not isinstance(slide_index, int):
            raise ApiError(400, "slide_index must be an integer.")
        if target_key not in ALLOWED_IMAGE_KEYS:
            raise ApiError(400, "target_key is not allowed.")

        plan_path = get_plan_path()
        plan = load_plan(plan_path)
        slides = plan.get("slides", [])
        if not isinstance(slides, list):
            raise ApiError(400, "slide_plan.json must contain a slides array.")
        if slide_index < 0 or slide_index >= len(slides):
            raise ApiError(400, "slide_index is out of range.")

        slide = slides[slide_index]
        if not isinstance(slide, dict):
            raise ApiError(400, "The selected slide is not an object.")

        slide_type = slide.get("layout", slide.get("type", ""))
        if slide_type == "image_comparison":
            if target_key not in {"LEFT_IMAGE_SRC", "RIGHT_IMAGE_SRC"}:
                raise ApiError(400, "image_comparison only accepts LEFT_IMAGE_SRC or RIGHT_IMAGE_SRC.")
        elif target_key != "IMAGE_SRC":
            raise ApiError(400, "This slide layout only accepts IMAGE_SRC.")

        image_src = save_uploaded_image(payload, slide_index, target_key)
        backup_path = backup_plan(plan_path)
        slide[target_key] = image_src
        save_plan_atomic(plan_path, plan)
        rebuild = rebuild_outputs()

        self.send_json_response(
            200,
            {
                "status": "success",
                "message": "Image uploaded and outputs rebuilt.",
                "image_src": image_src,
                "backup": backup_path.name,
                "rebuild": rebuild,
            },
        )

    def send_json_response(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)'''

py = re.sub(
    r'<<<<<<< HEAD\n            self.require_local_request\(\).*?>>>>>>> origin/main\n',
    do_post_resolved + '\n',
    py,
    flags=re.DOTALL
)

apply_text_edits_str = '''def apply_edit_to_slide(slide, edit_id, value):
    scalar_match = re.fullmatch(r'[A-Z_]+', edit_id)
    if scalar_match:
        slide[edit_id] = value
        return

    list_match = re.fullmatch(r'([A-Z_]+)\[(\d+)\](?:\.([A-Za-z_]+))?', edit_id)
    if not list_match:
        raise ValueError(f"지원하지 않는 편집 ID입니다: {edit_id}")

    key, index_text, prop = list_match.groups()
    index = int(index_text)
    items = slide.get(key)
    if not isinstance(items, list) or index >= len(items):
        raise ValueError(f"편집 대상 리스트를 찾을 수 없습니다: {edit_id}")

    if prop:
        if not isinstance(items[index], dict):
            items[index] = {"text": str(items[index])}
        items[index][prop] = value
    else:
        items[index] = value


def apply_text_edits(plan, edits, style_overrides):
    slides = plan.get('slides', [])
    for edit in edits or []:
        slide_index = edit.get('slideIndex')
        edit_id = edit.get('editId')
        value = edit.get('value', '')
        if not isinstance(slide_index, int) or slide_index < 0 or slide_index >= len(slides):
            raise ValueError(f"범위를 벗어난 슬라이드 번호입니다: {slide_index}")
        if not edit_id:
            continue
        apply_edit_to_slide(slides[slide_index], edit_id, value)

    for style in style_overrides or []:
        slide_index = style.get('slideIndex')
        edit_id = style.get('editId')
        font_size = style.get('fontSize')
        if not isinstance(slide_index, int) or slide_index < 0 or slide_index >= len(slides):
            raise ValueError(f"범위를 벗어난 스타일 슬라이드 번호입니다: {slide_index}")
        if not edit_id or not font_size:
            continue
        overrides = slides[slide_index].setdefault('STYLE_OVERRIDES', {})
        overrides[edit_id] = {"fontSize": font_size}


class DevServerHandler'''

py = py.replace('class DevServerHandler', apply_text_edits_str)

with open('.agents/skills/text-to-slide-architect/scripts/dev_server.py', 'w', encoding='utf-8') as f:
    f.write(py)
