#!/usr/bin/env python3
"""Local preview server for slide projects.

Run from a project directory that contains slide_plan.json:
    python ../.agents/skills/text-to-slide-architect/scripts/dev_server.py
"""

import base64
import binascii
import datetime as dt
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import urllib.parse
import copy
import re
import shutil
import time
import uuid
from pathlib import Path


HOST = "127.0.0.1"
PORT = 8000
SCRIPT_DIR = Path(__file__).resolve().parent
BUILD_HTML_PY = SCRIPT_DIR / "build_html.py"
CAPTURE_PNG_PY = SCRIPT_DIR / "capture_png.py"
EXPORT_IMAGE_PPTX_PY = SCRIPT_DIR / "export_image_pptx.py"

MAX_JSON_BODY_BYTES = 26 * 1024 * 1024
MAX_IMAGE_BYTES = 15 * 1024 * 1024
ALLOWED_IMAGE_KEYS = {"IMAGE_SRC", "LEFT_IMAGE_SRC", "RIGHT_IMAGE_SRC"}
ALLOWED_IMAGE_MIME = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/webp",
}


class ApiError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def get_plan_path() -> Path:
    return Path.cwd() / "slide_plan.json"


def safe_child_path(root: Path, rel_path: str) -> str:
    root = root.resolve()
    candidate = (root / rel_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return str(root / "__not_found__")
    return str(candidate)


def load_plan(plan_path: Path) -> dict:
    if not plan_path.exists():
        raise ApiError(
            404,
            "slide_plan.json was not found. Start the server from a slide project directory.",
        )

    with plan_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def backup_plan(plan_path: Path) -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = plan_path.with_name(f"slide_plan.backup.{timestamp}.json")
    if backup_path.exists():
        backup_path = plan_path.with_name(
            f"slide_plan.backup.{timestamp}.{uuid.uuid4().hex[:8]}.json"
        )
    shutil.copy2(plan_path, backup_path)
    return backup_path


def save_plan_atomic(plan_path: Path, plan: dict) -> None:
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{plan_path.name}.",
        suffix=".tmp",
        dir=str(plan_path.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_name, plan_path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def run_command(cmd, label: str):
    print(f"[SYS] {label}: {' '.join(str(part) for part in cmd)}")
    result = subprocess.run(
        [str(part) for part in cmd],
        cwd=str(Path.cwd()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        raise ApiError(500, f"{label} failed: {details}")
    return result


def rebuild_outputs() -> dict:
    plan_path = get_plan_path()
    output_dir = Path.cwd() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_html = output_dir / "index.html"
    run_command([sys.executable, BUILD_HTML_PY, plan_path, output_html], "HTML build")

    captured_dir = output_dir / "captured_images"
    run_command([sys.executable, CAPTURE_PNG_PY, output_html, captured_dir], "Slide capture")

    output_pptx = output_dir / "presentation.pptx"
    run_command(
        [sys.executable, EXPORT_IMAGE_PPTX_PY, captured_dir, output_pptx],
        "Image PPTX build",
    )

    return {
        "html": "output/index.html",
        "captures": "output/captured_images",
        "pptx": "output/presentation.pptx",
    }


def parse_host_name(raw_host: str) -> str:
    host = (raw_host or "").strip().lower()
    if host.startswith("[") and "]" in host:
        return host[1 : host.index("]")]
    return host.split(":", 1)[0]


def is_local_host(raw_host: str) -> bool:
    return parse_host_name(raw_host) in {"localhost", "127.0.0.1", "::1"}


def detect_image_type(raw: bytes):
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", ".png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", ".jpg"
    if raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a"):
        return "image/gif", ".gif"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "image/webp", ".webp"
    return None, None


def sanitize_filename_stem(filename: str) -> str:
    name = os.path.basename(filename or "image")
    stem = os.path.splitext(name)[0]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    return (stem or "image")[:48]


def decode_upload_image(image_data: str, filename: str, file_type: str = ""):
    if not isinstance(image_data, str) or not image_data:
        raise ApiError(400, "image_data is required.")

    declared_mime = (file_type or "").lower()
    base64_part = image_data

    if image_data.startswith("data:"):
        header, separator, data = image_data.partition(",")
        if separator != ",":
            raise ApiError(400, "Invalid image data URL.")

        match = re.match(r"^data:([^;]+);base64$", header, flags=re.IGNORECASE)
        if not match:
            raise ApiError(400, "Only base64 image data URLs are supported.")

        declared_mime = match.group(1).lower()
        base64_part = data

    if declared_mime and declared_mime not in ALLOWED_IMAGE_MIME:
        raise ApiError(415, "Unsupported image type. Use PNG, JPG, GIF, or WebP.")

    try:
        raw = base64.b64decode(base64_part, validate=True)
    except (binascii.Error, ValueError):
        raise ApiError(400, "Invalid base64 image data.")

    if not raw:
        raise ApiError(400, "The uploaded image is empty.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise ApiError(413, "The image is too large. Maximum size is 15 MB.")

    detected_mime, extension = detect_image_type(raw)
    if not detected_mime:
        raise ApiError(415, "Unsupported or invalid image file.")

    stem = sanitize_filename_stem(filename)
    return raw, detected_mime, extension, stem


def save_uploaded_image(payload: dict, slide_index: int, target_key: str) -> str:
    raw, _mime, extension, stem = decode_upload_image(
        payload.get("image_data", ""),
        payload.get("filename", ""),
        payload.get("file_type", ""),
    )

    images_dir = Path.cwd() / "output" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    key_part = target_key.lower()
    safe_name = f"upload_s{slide_index + 1}_{key_part}_{timestamp}_{uuid.uuid4().hex[:8]}_{stem}{extension}"
    image_path = images_dir / safe_name
    image_path.write_bytes(raw)
    return f"images/{safe_name}"


def read_json_body(handler):
    content_length = int(handler.headers.get('Content-Length', 0))
    post_data = handler.rfile.read(content_length)
    return json.loads(post_data.decode('utf-8') or '{}')



def apply_edit_to_slide(slide, edit_id, value):
    keys = edit_id.replace(']', '').replace('[', '.').split('.')
    keys = [k for k in keys if k]
    target = slide
    for i, k in enumerate(keys[:-1]):
        if k.isdigit():
            k = int(k)
        next_k = keys[i+1]
        is_next_digit = next_k.isdigit()
        
        if isinstance(target, dict):
            if k not in target:
                target[k] = [] if is_next_digit else {}
            target = target[k]
        elif isinstance(target, list):
            while len(target) <= k:
                target.append([] if is_next_digit else {})
            if isinstance(target[k], str) and not is_next_digit:
                target[k] = {"text": target[k]}
            target = target[k]
            
    last_key = keys[-1]
    if last_key.isdigit():
        last_key = int(last_key)
        
    if isinstance(target, list):
        while len(target) <= last_key:
            target.append("")
        target[last_key] = value
    else:
        target[last_key] = value


def apply_text_edits(plan, edits, style_overrides):
    slides = plan.get('pages') if isinstance(plan.get('pages'), list) else plan.get('slides', [])
    for edit in edits or []:
        slide_index = edit.get('slideIndex')
        edit_id = edit.get('editId')
        value = edit.get('value', '')
        if not edit_id:
            continue
        if edit_id.startswith('$root.'):
            apply_edit_to_slide(plan, edit_id[6:], value)
            continue
        if not isinstance(slide_index, int) or slide_index < 0 or slide_index >= len(slides):
            raise ValueError(f"범위를 벗어난 슬라이드 번호입니다: {slide_index}")
        apply_edit_to_slide(slides[slide_index], edit_id, value)

    for style in style_overrides or []:
        slide_index = style.get('slideIndex')
        edit_id = style.get('editId')
        font_size = style.get('fontSize')
        if not edit_id or not font_size:
            continue
        if edit_id.startswith('$root.'):
            continue
        if not isinstance(slide_index, int) or slide_index < 0 or slide_index >= len(slides):
            raise ValueError(f"범위를 벗어난 스타일 슬라이드 번호입니다: {slide_index}")
        overrides = slides[slide_index].setdefault('STYLE_OVERRIDES', {})
        overrides[edit_id] = {"fontSize": font_size}

class DevServerHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path

        if clean_path == "/":
            return str(Path.cwd() / "output" / "index.html")

        if clean_path.startswith("/output/"):
            rel_path = clean_path[8:]
            return safe_child_path(Path.cwd() / "output", rel_path)

        for asset_dir in ["images", "diagrams", "includes", "audio"]:
            if clean_path.startswith(f"/{asset_dir}/"):
                return safe_child_path(Path.cwd() / "output", clean_path.lstrip("/"))

        return super().translate_path(path)

    def read_json_payload(self) -> dict:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ApiError(400, "Invalid Content-Length header.")

        if content_length <= 0:
            raise ApiError(400, "Request body is required.")
        if content_length > MAX_JSON_BODY_BYTES:
            raise ApiError(413, "Request body is too large.")

        post_data = self.rfile.read(content_length)
        try:
            payload = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            raise ApiError(400, "Invalid JSON payload.")

        if not isinstance(payload, dict):
            raise ApiError(400, "JSON payload must be an object.")
        return payload

    def require_local_request(self):
        if not is_local_host(self.headers.get("Host", "")):
            raise ApiError(403, "Only local requests are allowed.")

        origin = self.headers.get("Origin")
        if origin:
            origin_host = urllib.parse.urlparse(origin).netloc
            if not is_local_host(origin_host):
                raise ApiError(403, "Only local origins are allowed.")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            self.require_local_request()

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
        target_key = "pages" if isinstance(plan.get("pages"), list) else "slides"
        original_pages = plan.get(target_key, [])
        if not isinstance(original_pages, list):
            raise ApiError(400, f"slide_plan.json must contain a {target_key} array.")

        new_pages = []
        for idx in indices:
            if isinstance(idx, bool) or not isinstance(idx, int):
                raise ApiError(400, "indices must contain integers only.")
            if idx < 0 or idx >= len(original_pages):
                raise ApiError(400, f"Invalid slide index: {idx}")
            new_pages.append(original_pages[idx])

        backup_path = backup_plan(plan_path)
        plan[target_key] = new_pages
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
        self.wfile.write(body)

    def send_error_response(self, code, message):
        self.send_json_response(code, {"status": "error", "message": message})


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def run(port=PORT):
    plan_path = get_plan_path()
    if not plan_path.exists():
        print("[WARN] slide_plan.json was not found in the current directory.")
        print("       Run this server from a slide project directory.")
        print("       Example: cd 260619_grade3_history")
        sys.exit(1)

    current_port = port
    max_attempts = 20
    httpd = None

    for _ in range(max_attempts):
        try:
            server_address = (HOST, current_port)
            httpd = ThreadingHTTPServer(server_address, DevServerHandler)
            break
        except OSError:
            print(f"[INFO] Port {current_port} is in use. Trying {current_port + 1}.")
            current_port += 1

    if not httpd:
        print("[ERROR] Could not allocate a local preview port.")
        sys.exit(1)

    print("[SUCCESS] Slide local preview server is running.")
    print(f"   * Preview: http://localhost:{current_port}")
    print(f"   * Bound to: {HOST}:{current_port}")
    print(f"   * Project: {Path.cwd()}")
    print("   * Stop: Ctrl+C")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()


if __name__ == "__main__":
    run()
