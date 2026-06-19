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

PORT = 8000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_HTML_PY = os.path.join(SCRIPT_DIR, 'build_html.py')


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
        for asset_dir in ['images', 'diagrams', 'includes']:
            if clean_path.startswith(f'/{asset_dir}/'):
                return os.path.join(os.getcwd(), 'output', clean_path.lstrip('/'))

        return super().translate_path(path)

    def do_POST(self):
        """POST /api/save-order API 요청을 처리합니다."""
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/save-order':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                req_json = json.loads(post_data.decode('utf-8'))
                indices = req_json.get('indices', [])
                
                # slide_plan.json 정렬 및 삭제 저장
                plan_path = os.path.join(os.getcwd(), 'slide_plan.json')
                if not os.path.exists(plan_path):
                    self.send_error_response(404, "slide_plan.json 파일을 찾을 수 없습니다. 현재 프로젝트 폴더 내에서 서버가 실행되었는지 확인해 주세요.")
                    return
                
                with open(plan_path, 'r', encoding='utf-8') as f:
                    plan = json.load(f)
                
                original_slides = plan.get('slides', [])
                
                # 인덱스 검증
                new_slides = []
                for idx in indices:
                    if 0 <= idx < len(original_slides):
                        new_slides.append(original_slides[idx])
                    else:
                        print(f"[경고] 올바르지 않은 슬라이드 인덱스 무시: {idx}")
                
                # 저장
                plan['slides'] = new_slides
                with open(plan_path, 'w', encoding='utf-8') as f:
                    json.dump(plan, f, ensure_ascii=False, indent=2)
                
                print(f"[API] slide_plan.json 슬라이드 구성 갱신 완료 (남은 슬라이드: {len(new_slides)}장)")
                
                # html 빌더 실행 (build_html.py)
                output_html = os.path.join(os.getcwd(), 'output', 'index.html')
                cmd = [sys.executable, BUILD_HTML_PY, plan_path, output_html]
                
                print(f"[SYS] HTML 빌드 자동 실행: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
                
                if result.returncode != 0:
                    print(f"[오류] 빌드 실패: {result.stderr}")
                    self.send_error_response(500, f"HTML 빌드 실패: {result.stderr}")
                    return
                
                # 1. 네이티브 PPTX 자동 재생성
                output_pptx = os.path.join(os.getcwd(), 'output', 'presentation.pptx')
                export_pptx_py = os.path.join(SCRIPT_DIR, 'export_pptx.py')
                pptx_cmd = [sys.executable, export_pptx_py, plan_path, output_pptx, os.path.join(os.getcwd(), 'output')]
                print(f"[SYS] 네이티브 PPTX 빌드 자동 실행: {' '.join(pptx_cmd)}")
                subprocess.run(pptx_cmd, capture_output=True)
                
                # 2. 슬라이드 스크린샷(PNG) 자동 캡처
                output_images_dir = os.path.join(os.getcwd(), 'output', 'captured_images')
                capture_png_py = os.path.join(SCRIPT_DIR, 'capture_png.py')
                capture_cmd = [sys.executable, capture_png_py, output_html, output_images_dir]
                print(f"[SYS] 슬라이드 스크린샷 캡처 자동 실행: {' '.join(capture_cmd)}")
                capture_res = subprocess.run(capture_cmd, capture_output=True)
                
                # 3. 이미지형 PPTX 자동 재생성 (캡처 성공 시)
                if capture_res.returncode == 0:
                    output_image_pptx = os.path.join(os.getcwd(), 'output', 'presentation_images.pptx')
                    export_img_pptx_py = os.path.join(SCRIPT_DIR, 'export_image_pptx.py')
                    img_pptx_cmd = [sys.executable, export_img_pptx_py, output_images_dir, output_image_pptx]
                    print(f"[SYS] 이미지형 PPTX 빌드 자동 실행: {' '.join(img_pptx_cmd)}")
                    subprocess.run(img_pptx_cmd, capture_output=True)
                
                # 성공 응답
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {"status": "success", "message": "슬라이드 정렬 및 삭제 완료, HTML/PPTX/이미지 빌드 성공!"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                
            except Exception as e:
                print(f"[오류] 요청 처리 중 예외 발생: {e}")
                self.send_error_response(500, f"서버 처리 오류: {str(e)}")
        else:
            self.send_error_response(404, "API 엔드포인트를 찾을 수 없습니다.")

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
