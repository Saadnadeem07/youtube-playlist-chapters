import subprocess
import sys
import yt_dlp
from pathlib import Path

ROOT = Path(__file__).parent
PYTHON = sys.executable
PLAYLIST_FILE = ROOT / "playlist_videos.txt"
FINAL_FILE = ROOT / "final_output.txt"
SEP = "-" * 40

def is_playlist_url(url):
    return "/playlist" in url or ("list=" in url and "watch?" not in url)

def run_playlist(playlist_url):
    print("Fetching playlist...")
    subprocess.run(
        [PYTHON, str(ROOT / "fetch_playlist.py"), playlist_url, str(PLAYLIST_FILE)],
        check=True,
    )

def parse_playlist():
    videos = []
    lines = PLAYLIST_FILE.read_text(encoding="utf-8").splitlines()
    i = 0
    while i + 1 < len(lines):
        title = lines[i].strip()
        url = lines[i + 1].strip()
        if title and url.startswith("http"):
            videos.append((title, url))
        i += 3
    seen = set()
    unique = []
    for t, u in videos:
        if u not in seen:
            seen.add(u)
            unique.append((t, u))
    return unique

def get_chapters(url):
    result = subprocess.run(
        [PYTHON, str(ROOT / "fetch_chapters.py"), url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return "No chapters found"
    out = result.stdout.strip()
    return out if out else "No chapters found"

def get_title(video_url):
    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(video_url, download=False)
    return info.get("title", "No Title")

def process_playlist(playlist_url):
    run_playlist(playlist_url)
    videos = parse_playlist()
    print(f"Parsed {len(videos)} unique videos")

    with FINAL_FILE.open("w", encoding="utf-8") as f:
        for idx, (title, url) in enumerate(videos, 1):
            print(f"[{idx}/{len(videos)}] {title}")
            chapters = get_chapters(url)
            f.write(f"{title}\n{url}\n{chapters}\n{SEP}\n\n")

    print(f"Done. Wrote {FINAL_FILE}")

def process_video(video_url):
    print("Fetching video metadata...")
    title = get_title(video_url)
    print(f"Video: {title}")
    chapters = get_chapters(video_url)

    with FINAL_FILE.open("w", encoding="utf-8") as f:
        f.write(f"{title}\n{video_url}\n{chapters}\n{SEP}\n\n")

    print(f"Done. Wrote {FINAL_FILE}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <playlist_url | video_url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    if is_playlist_url(url):
        process_playlist(url)
    else:
        process_video(url)

if __name__ == "__main__":
    main()
