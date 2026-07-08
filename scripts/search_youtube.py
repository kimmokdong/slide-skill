import os
import sys
import json
import isodate
import argparse
from googleapiclient.discovery import build

def get_api_key():
    # 1. Try to read from .env files
    env_paths = [
        os.path.join(os.path.dirname(__file__), '..', '.env'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '.env'), # Local project root
    ]
    for p in env_paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('YOUTUBE_API_KEY='):
                        return line.split('=', 1)[1].strip()

    # 2. Check system environment variable
    if 'YOUTUBE_API_KEY' in os.environ:
        return os.environ['YOUTUBE_API_KEY']

    # 3. Fallback to old txt files
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'youtube_api_key.txt'),
        os.path.join(os.path.dirname(__file__), '..', 'youtube_api_key.txt'),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return f.read().strip()
    return None

def search_youtube(query: str, max_results: int = 5):
    api_key = get_api_key()
    if not api_key:
        print(json.dumps({"error": "youtube_api_key.txt not found."}))
        sys.exit(1)

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # 1. Search for videos
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=max_results,
            type='video',
            relevanceLanguage='ko',
            safeSearch='moderate'
        ).execute()

        video_ids = []
        for item in search_response.get('items', []):
            video_ids.append(item['id']['videoId'])

        if not video_ids:
            print(json.dumps({"results": []}))
            return

        # 2. Get video details (for duration & view counts)
        video_response = youtube.videos().list(
            id=','.join(video_ids),
            part='snippet,contentDetails,statistics'
        ).execute()

        results = []
        for item in video_response.get('items', []):
            vid_id = item['id']
            title = item['snippet']['title']
            channel = item['snippet']['channelTitle']
            
            # Parse ISO 8601 duration
            duration_iso = item['contentDetails']['duration']
            try:
                duration_dt = isodate.parse_duration(duration_iso)
                total_seconds = int(duration_dt.total_seconds())
                m, s = divmod(total_seconds, 60)
                h, m = divmod(m, 60)
                if h > 0:
                    duration_str = f"{h}시간 {m}분 {s}초"
                else:
                    duration_str = f"{m}분 {s}초"
            except Exception:
                duration_str = "알 수 없음"

            views = int(item['statistics'].get('viewCount', 0))
            views_str = f"{views:,}회" if views > 0 else "조회수 없음"

            results.append({
                "video_id": vid_id,
                "title": title,
                "channel": channel,
                "duration": duration_str,
                "views": views_str,
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "thumbnail": item['snippet']['thumbnails']['high']['url']
            })

        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Search YouTube")
    parser.add_argument('query', type=str, help="Search query")
    parser.add_argument('--max', type=int, default=3, help="Max results")
    args = parser.parse_args()
    
    search_youtube(args.query, args.max)
