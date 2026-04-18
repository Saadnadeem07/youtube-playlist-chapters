import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PYTHON = sys.executable
PLAYLIST_FILE = ROOT / "playlist_videos.txt"
FINAL_FILE = ROOT / "final_output.txt"
SEP = "-" * 40

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

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <playlist_url>", file=sys.stderr)
        sys.exit(1)

    playlist_url = sys.argv[1]
    run_playlist(playlist_url)
    videos = parse_playlist()
    print(f"Parsed {len(videos)} unique videos")

    with FINAL_FILE.open("w", encoding="utf-8") as f:
        for idx, (title, url) in enumerate(videos, 1):
            print(f"[{idx}/{len(videos)}] {title}")
            chapters = get_chapters(url)
            f.write(f"{title}\n{url}\n{chapters}\n{SEP}\n\n")

    print(f"Done. Wrote {FINAL_FILE}")

if __name__ == "__main__":
    main()
