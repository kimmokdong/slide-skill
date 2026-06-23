#!/usr/bin/env python3
"""경량 로컬 개발 서버 및 슬라이드 순서/삭제 동기화 서버.

사용법:
    프로젝트 폴더(예: 260619_grade3_history) 안에서 실행:
    python ../.agents/skills/text-to-slide-architect/scripts/dev_server.py
"""

import http.server
import socketserver
import json
import os
import sys
import subprocess
import urllib.parse
import copy
import re
import shutil
import time

PORT = 8000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_HTML_PY = os.path.join(SCRIPT_DIR, 'build_html.py')


def read_json_body(handler):
    content_length = int(handler.headers.get('Content-Length', 0))
    post_data = handler.rfile.read(content_length)
    return json.loads(post_data.decode('utf-8') or '{}')


def get_plan_path():
    return os.path.join(os.getcwd(), 'slide_plan.json')


def get_output_html_path():
    return os.path.join(os.getcwd(), 'output', 'index.html')


def load_plan():
    plan_path = get_plan_path()
    if not os.path.exists(plan_path):
        raise FileNotFoundError("slide_plan.json 파일을 찾을 수 없습니다.")
    with open(plan_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_plan(path, plan):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def validate_indices(indices, slide_count):
    if not isinstance(indices, list):
        raise ValueError("indices는 배열이어야 합니다.")
    if not indices:
        raise ValueError("최소 1장의 슬라이드는 남아 있어야 합니다.")
    if len(set(indices)) != len(indices):
        raise ValueError("중복된 슬라이드 인덱스가 있습니다.")
    for idx in indices:
        if not isinstance(idx, int) or idx < 0 or idx >= slide_count:
            raise ValueError(f"범위를 벗어난 슬라이드 인덱스입니다: {idx}")


def build_html_from_plan(plan_path, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cmd = [sys.executable, BUILD_HTML_PY, plan_path, output_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "HTML build failed")


def commit_plan_after_success(plan, response_message):
    plan_path = get_plan_path()
    output_html = get_output_html_path()
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(os.getcwd(), f'slide_plan.backup.{timestamp}.json')
    tmp_plan_path = os.path.join(os.getcwd(), f'.slide_plan.pending.{timestamp}.json')
    tmp_html_path = os.path.join(os.getcwd(), 'output', f'.index.pending.{timestamp}.html')

    try:
        write_plan(tmp_plan_path, plan)
        build_html_from_plan(tmp_plan_path, tmp_html_path)

        shutil.copy2(plan_path, backup_path)
        os.replace(tmp_plan_path, plan_path)
        os.replace(tmp_html_path, output_html)
        
        # 만약 작업 폴더에 inject_audio.py가 있다면 실행 (오디오 태그 복구)
        audio_script = os.path.join(os.getcwd(), 'inject_audio.py')
        if os.path.exists(audio_script):
            subprocess.run([sys.executable, 'inject_audio.py'], capture_output=True)
            
        # 자동 청소 로직: 최근 5개의 백업 파일만 유지하고 나머지는 삭제
        try:
            cwd = os.getcwd()
            backup_files = sorted([f for f in os.listdir(cwd) if f.startswith('slide_plan.backup.') and f.endswith('.json')])
            if len(backup_files) > 5:
                for old_backup in backup_files[:-5]:
                    os.remove(os.path.join(cwd, old_backup))
        except Exception as e:
            print(f"Backup cleanup failed: {e}")
    except Exception:
        for path in [tmp_plan_path, tmp_html_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        raise

    return {
        "status": "success",
        "message": response_message,
        "backup": os.path.basename(backup_path)
    }


def apply_edit_to_slide(slide, edit_id, value):
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


class DevServerHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        """루트('/') 요청 시 output/index.html을 서빙하도록 랩핑하고,
        에셋 리소스도 프로젝트 구조에 맞게 매핑해줍니다."""
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path

        # 루트 경로 요청 시 output/index.html 제공
        if clean_path == '/':
            return os.path.join(os.getcwd(), 'output', 'index.html')
            
        # /output/ 으로 시작하는 리소스
        if clean_path.startswith('/output/'):
            rel_path = clean_path[8:] # /output/ 제거
            return os.path.join(os.getcwd(), 'output', rel_path)
            
        # /images/ 또는 /diagrams/ 등의 에셋 매핑 지원 (HTML 상에서 images/name.png 로 가리키는 경우)
        for asset_dir in ['images', 'diagrams', 'includes', 'audio']:
            if clean_path.startswith(f'/{asset_dir}/'):
                return os.path.join(os.getcwd(), 'output', clean_path.lstrip('/'))

        return super().translate_path(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        try:
            if parsed.path == '/api/save-order':
                req_json = read_json_body(self)
                indices = req_json.get('indices', [])
                plan = load_plan()
                original_slides = plan.get('slides', [])
                validate_indices(indices, len(original_slides))
                plan['slides'] = [copy.deepcopy(original_slides[idx]) for idx in indices]
                response = commit_plan_after_success(plan, "슬라이드 순서/삭제 저장 완료")
                self.send_json_response(200, response)
                return

            if parsed.path == '/api/save-theme':
                req_json = read_json_body(self)
                theme_colors = req_json.get('theme_colors')
                if not isinstance(theme_colors, dict):
                    raise ValueError("theme_colors는 객체여야 합니다.")
                plan = load_plan()
                plan.setdefault('meta', {})['theme_colors'] = theme_colors
                response = commit_plan_after_success(plan, "테마 저장 완료")
                self.send_json_response(200, response)
                return

            if parsed.path == '/api/save-text-edits':
                req_json = read_json_body(self)
                plan = load_plan()
                apply_text_edits(
                    plan,
                    req_json.get('edits', []),
                    req_json.get('style_overrides', [])
                )
                response = commit_plan_after_success(plan, "텍스트 직접 편집 저장 완료")
                self.send_json_response(200, response)
                return

            self.send_error_response(404, "API 엔드포인트를 찾을 수 없습니다.")
        except FileNotFoundError as e:
            self.send_error_response(404, str(e))
        except ValueError as e:
            self.send_error_response(400, str(e))
        except Exception as e:
            print(f"[오류] 요청 처리 중 예외 발생: {e}")
            self.send_error_response(500, f"서버 처리 오류: {str(e)}")

    def send_json_response(self, code, payload):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        err_res = {"status": "error", "message": message}
        self.wfile.write(json.dumps(err_res).encode('utf-8'))


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """멀티스레딩 지원 서버로 브라우저의 다중 정적 파일 로드 병목을 방지합니다."""
    daemon_threads = True


def run(port=PORT):
    # slide_plan.json 존재 여부 체크 가이드
    plan_path = os.path.join(os.getcwd(), 'slide_plan.json')
    if not os.path.exists(plan_path):
        print("[주의] 현재 작업 디렉터리에 slide_plan.json이 존재하지 않습니다.")
        print("  반드시 슬라이드 프로젝트 폴더(예: 260619_grade3_history) 안으로 CWD를 맞춰 실행해 주세요.")
        print("  예: cd 260619_grade3_history && python ../.agents/skills/text-to-slide-architect/scripts/dev_server.py")
        sys.exit(1)
        
    current_port = port
    max_attempts = 20
    httpd = None
    
    # 포트 충돌 시 자동으로 다음 포트 감지 및 전환
    for i in range(max_attempts):
        try:
            server_address = ('', current_port)
            httpd = ThreadingHTTPServer(server_address, DevServerHandler)
            break
        except OSError:
            print(f"[알림] 포트 {current_port}번이 사용 중입니다. 다음 포트({current_port + 1}번)로 자동 조회를 시도합니다.")
            current_port += 1
            
    if not httpd:
        print("[오류] 가용한 로컬 포트를 할당받지 못했습니다.")
        sys.exit(1)
        
    print("[SUCCESS] 바이브코딩 로컬 개발 서버가 구동되었습니다!")
    print(f"   * 슬라이드 보기: http://localhost:{current_port}")
    print(f"   * 프로젝트 폴더: {os.getcwd()}")
    print("   * 종료하려면 Ctrl+C를 누르세요.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 안전하게 종료합니다.")
        httpd.server_close()


if __name__ == '__main__':
    run()
