import sys
import yt_dlp

def fetch_playlist(playlist_url, output_file):
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)

    entries = info.get("entries") or []
    with open(output_file, "w", encoding="utf-8") as f:
        for video in entries:
            title = video.get("title", "No Title")
            url = f"https://www.youtube.com/watch?v={video.get('id')}"
            f.write(f"{title}\n{url}\n{'-' * 40}\n")

    return len(entries)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_playlist.py <playlist_url> [output_file]", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "playlist_videos.txt"
    count = fetch_playlist(url, out)
    print(f"Saved {count} videos to {out}")
