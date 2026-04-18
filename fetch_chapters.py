import sys
import yt_dlp

def format_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hrs:02}:{mins:02}:{secs:02}"

def get_chapters(video_url):
    ydl_opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    chapters = info.get("chapters") or []
    if not chapters:
        return "No chapters found"

    lines = []
    for ch in chapters:
        start = format_time(ch["start_time"])
        lines.append(f"{start} - {ch.get('title', '')}")
    return "\n".join(lines)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_chapters.py <video_url>", file=sys.stderr)
        sys.exit(1)
    print(get_chapters(sys.argv[1]))
