#!/usr/bin/env python3
"""
YouTube Playlist Downloader — a tiny, dependency-free local web app.

Paste a playlist (or single video) URL, browse every video, pick a quality, and
download them all, a selection, or one-by-one — each with a live progress bar.

No third-party Python packages required: this uses only the standard library and
shells out to the ``yt-dlp`` binary (with ``ffmpeg`` for merging audio + video).

Usage:
    python3 app.py                 # then open http://127.0.0.1:8000
    PORT=9000 python3 app.py       # custom port

Downloads are saved to the ./downloads folder next to this script.
"""

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(HERE, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))

YTDLP = shutil.which("yt-dlp")
FFMPEG = shutil.which("ffmpeg")

ANSI = re.compile(r"\x1b\[[0-9;]*m")

# yt-dlp format selectors keyed by the quality value the UI sends.
FORMAT_SELECTORS = {
    "best": "bestvideo+bestaudio/best",
    "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480": "bestvideo[height<=480]+bestaudio/best[height<=480]",
}

# ---------------------------------------------------------------------------
# Shared state: a single background worker downloads sequentially from a queue.
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_status = {}          # vid -> {state, percent, speed, eta, file, error, title}
_meta = {}            # vid -> {"title": ..., "url": ..., "format": ...}
_procs = {}           # vid -> subprocess.Popen (only while actively running)
_cancelled = set()    # vids the user asked to cancel
_dlqueue = queue.Queue()


def set_status(vid, **kw):
    with _lock:
        s = _status.setdefault(vid, {
            "vid": vid, "title": "", "state": "idle",
            "percent": 0, "speed": "", "eta": "", "file": "", "error": "",
        })
        s.update(kw)


def find_output_file(vid):
    """Best-effort: find the finished file by its [<id>] tag in the name."""
    for name in os.listdir(DOWNLOAD_DIR):
        if f"[{vid}]" in name:
            return name
    return ""


def build_cmd(url, fmt, out_tmpl):
    """Assemble the yt-dlp command for a given quality choice."""
    base = [
        YTDLP,
        "--no-playlist",
        "--no-color",
        "--newline",
        "--progress-template",
        "PR|%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        "-o", out_tmpl,
    ]
    if fmt == "audio":
        # Extract audio only and transcode to mp3.
        return base + ["-f", "bestaudio/best", "-x", "--audio-format", "mp3", url]
    selector = FORMAT_SELECTORS.get(fmt, FORMAT_SELECTORS["best"])
    return base + ["-f", selector, "--merge-output-format", "mp4", url]


def do_download(vid):
    # Skip anything cancelled while it was still waiting in the queue.
    with _lock:
        if vid in _cancelled:
            _cancelled.discard(vid)
            set_status(vid, state="cancelled", percent=0)
            return

    meta = _meta.get(vid, {})
    url = meta.get("url") or f"https://www.youtube.com/watch?v={vid}"
    title = meta.get("title", "")
    fmt = meta.get("format", "best")
    set_status(vid, state="downloading", percent=0, error="", title=title)

    ext = "%(ext)s"
    out_tmpl = os.path.join(DOWNLOAD_DIR, f"%(title)s [%(id)s].{ext}")
    cmd = build_cmd(url, fmt, out_tmpl)

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1,
    )
    with _lock:
        _procs[vid] = proc

    last_err = ""
    for raw in proc.stdout:
        line = ANSI.sub("", raw).rstrip("\n")
        if line.startswith("PR|"):
            parts = line.split("|")
            pct_txt = parts[1].strip().replace("%", "")
            try:
                pct = float(pct_txt)
            except ValueError:
                pct = None
            kw = {"state": "downloading",
                  "speed": parts[2].strip(), "eta": parts[3].strip()}
            if pct is not None:
                kw["percent"] = pct
            set_status(vid, **kw)
        elif "Merging formats" in line or "[Merger]" in line:
            set_status(vid, state="merging", percent=100)
        elif "[ExtractAudio]" in line:
            set_status(vid, state="merging", percent=100)
        elif "ERROR:" in line:
            last_err = line.replace("ERROR:", "").strip()

    proc.wait()
    with _lock:
        _procs.pop(vid, None)
        was_cancelled = vid in _cancelled
        _cancelled.discard(vid)

    if was_cancelled:
        set_status(vid, state="cancelled", percent=0,
                   error="", file=find_output_file(vid))
    elif proc.returncode == 0:
        set_status(vid, state="done", percent=100, file=find_output_file(vid))
    else:
        set_status(vid, state="error",
                   error=last_err or f"yt-dlp exited with code {proc.returncode}")


def cancel_download(vid):
    """Cancel a queued or in-progress download."""
    with _lock:
        _cancelled.add(vid)
        proc = _procs.get(vid)
    if proc and proc.poll() is None:
        proc.terminate()
    else:
        # Not running yet (still queued) — mark it so the worker skips it.
        set_status(vid, state="cancelled", percent=0)


def worker():
    while True:
        vid = _dlqueue.get()
        try:
            do_download(vid)
        except Exception as e:  # noqa: BLE001 — surface any failure to the UI
            set_status(vid, state="error", error=str(e))
        finally:
            _dlqueue.task_done()


threading.Thread(target=worker, daemon=True).start()


# ---------------------------------------------------------------------------
# yt-dlp helpers
# ---------------------------------------------------------------------------
def list_playlist(url):
    """Return (playlist_title, [video dicts]) using a fast flat extraction."""
    if not url:
        raise ValueError("Please paste a YouTube playlist or video URL.")
    cmd = [YTDLP, "--flat-playlist", "--no-warnings", "--no-color", "-J", url]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or "yt-dlp failed to read the URL")
    data = json.loads(out.stdout)

    entries = data.get("entries")
    videos = []
    if entries is not None:
        title = data.get("title") or "Playlist"
        for e in entries:
            if not e:
                continue
            vid = e.get("id")
            if not vid:
                continue
            videos.append({
                "id": vid,
                "title": e.get("title") or "(unavailable)",
                "duration": e.get("duration"),
                "url": e.get("url") or f"https://www.youtube.com/watch?v={vid}",
                "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                "uploader": e.get("uploader") or e.get("channel") or "",
            })
    else:
        # A single video URL (no playlist).
        vid = data.get("id")
        title = data.get("title") or "Video"
        if vid:
            videos.append({
                "id": vid,
                "title": title,
                "duration": data.get("duration"),
                "url": data.get("webpage_url") or url,
                "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
                "uploader": data.get("uploader") or "",
            })
    return title, videos


def open_folder():
    """Open the downloads folder in the OS file manager (cross-platform)."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", DOWNLOAD_DIR])
    elif sys.platform.startswith("win"):
        os.startfile(DOWNLOAD_DIR)  # noqa: S606 — known, trusted path
    else:
        subprocess.Popen(["xdg-open", DOWNLOAD_DIR])


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YouTube Playlist Downloader</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⬇️</text></svg>">
<style>
  :root{
    --bg:#0b0d12; --bg-soft:#11141c; --panel:#151926; --panel-2:#1b2030;
    --border:#252b3b; --border-soft:#1d2231;
    --text:#e9ecf4; --muted:#9aa3ba; --faint:#6b7388;
    --brand:#3b82f6; --brand-2:#2563eb; --brand-ghost:rgba(59,130,246,.14);
    --ok:#22c55e; --warn:#f59e0b; --err:#ef4444; --accent:#a855f7;
    --radius:14px; --radius-sm:10px;
    --shadow:0 10px 30px rgba(0,0,0,.35);
  }
  [data-theme="light"]{
    --bg:#f5f7fb; --bg-soft:#eef1f7; --panel:#ffffff; --panel-2:#f3f5fa;
    --border:#e2e7f0; --border-soft:#eaeef5;
    --text:#0f1525; --muted:#5b6478; --faint:#8a93a8;
    --brand-ghost:rgba(37,99,235,.10);
    --shadow:0 10px 30px rgba(15,23,42,.10);
  }
  *{ box-sizing:border-box; }
  html,body{ height:100%; }
  body{
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    margin:0; background:radial-gradient(1200px 600px at 80% -10%, var(--brand-ghost), transparent 60%), var(--bg);
    color:var(--text); -webkit-font-smoothing:antialiased; line-height:1.45;
  }
  a{ color:var(--brand); }
  .wrap{ max-width:980px; margin:0 auto; padding:0 18px; }

  /* Header */
  header{
    position:sticky; top:0; z-index:20; backdrop-filter:blur(10px);
    background:color-mix(in srgb, var(--bg) 82%, transparent);
    border-bottom:1px solid var(--border);
  }
  .head-row{ display:flex; align-items:center; gap:12px; padding:14px 0; }
  .logo{ display:flex; align-items:center; gap:10px; font-weight:700; font-size:16px; }
  .logo .mark{
    width:32px; height:32px; border-radius:9px; display:grid; place-items:center;
    background:linear-gradient(135deg,var(--brand),var(--accent)); color:#fff; font-size:17px;
    box-shadow:0 4px 14px var(--brand-ghost);
  }
  .logo small{ display:block; font-weight:500; color:var(--muted); font-size:11px; }
  .grow{ flex:1; }
  .icon-btn{
    width:36px; height:36px; border-radius:10px; border:1px solid var(--border);
    background:var(--panel); color:var(--text); cursor:pointer; font-size:15px;
    display:grid; place-items:center; transition:.15s;
  }
  .icon-btn:hover{ background:var(--panel-2); transform:translateY(-1px); }
  .ghost-link{ color:var(--muted); text-decoration:none; font-size:13px; padding:0 6px; }
  .ghost-link:hover{ color:var(--text); }

  /* Search / load bar */
  .search{
    display:flex; gap:10px; padding:16px; margin:18px 0; flex-wrap:wrap;
    background:var(--panel); border:1px solid var(--border); border-radius:var(--radius);
    box-shadow:var(--shadow);
  }
  .field{ position:relative; flex:1; min-width:240px; }
  .field svg{ position:absolute; left:12px; top:50%; transform:translateY(-50%); opacity:.5; }
  input[type=text]{
    width:100%; padding:12px 12px 12px 38px; border-radius:var(--radius-sm);
    border:1px solid var(--border); background:var(--bg-soft); color:var(--text);
    font-size:14px; outline:none; transition:.15s;
  }
  input[type=text]:focus{ border-color:var(--brand); box-shadow:0 0 0 3px var(--brand-ghost); }
  select{
    padding:0 12px; height:44px; border-radius:var(--radius-sm); border:1px solid var(--border);
    background:var(--bg-soft); color:var(--text); font-size:14px; cursor:pointer; outline:none;
  }
  button{
    padding:0 18px; height:44px; border-radius:var(--radius-sm); border:1px solid transparent;
    background:var(--brand); color:#fff; font-size:14px; font-weight:600; cursor:pointer;
    display:inline-flex; align-items:center; gap:7px; transition:.15s; white-space:nowrap;
  }
  button:hover{ background:var(--brand-2); transform:translateY(-1px); }
  button:active{ transform:translateY(0); }
  button.secondary{ background:var(--panel-2); color:var(--text); border-color:var(--border); }
  button.secondary:hover{ background:var(--border-soft); }
  button.tiny{ height:34px; padding:0 12px; font-size:13px; }
  button:disabled{ opacity:.45; cursor:not-allowed; transform:none; }

  /* Toolbar */
  .toolbar{
    display:flex; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:14px;
  }
  .pl-title{ font-size:15px; font-weight:700; }
  .pl-sub{ color:var(--muted); font-size:13px; }
  .chk{ display:inline-flex; align-items:center; gap:7px; color:var(--muted); font-size:13px; cursor:pointer; user-select:none; }
  .chk input{ width:16px; height:16px; accent-color:var(--brand); cursor:pointer; }
  .mini-search{ min-width:170px; }
  .mini-search input{ height:38px; padding-left:34px; }

  /* Overall progress */
  .overall{
    display:none; align-items:center; gap:12px; padding:12px 14px; margin-bottom:14px;
    background:var(--panel); border:1px solid var(--border); border-radius:var(--radius-sm);
  }
  .overall.show{ display:flex; }
  .overall .track{ flex:1; height:8px; border-radius:6px; background:var(--bg-soft); overflow:hidden; }
  .overall .track > i{ display:block; height:100%; width:0%; border-radius:6px;
    background:linear-gradient(90deg,var(--brand),var(--accent)); transition:width .4s ease; }
  .overall .label{ font-size:13px; color:var(--muted); white-space:nowrap; }

  /* List */
  #list{ display:flex; flex-direction:column; gap:10px; padding-bottom:60px; }
  .row{
    display:flex; gap:14px; align-items:center; padding:12px;
    border:1px solid var(--border); border-radius:var(--radius); background:var(--panel);
    transition:.15s; position:relative;
  }
  .row:hover{ border-color:color-mix(in srgb, var(--brand) 40%, var(--border)); }
  .row.sel{ border-color:var(--brand); background:color-mix(in srgb, var(--brand) 6%, var(--panel)); }
  .row.hidden{ display:none; }
  .row .pick{ width:18px; height:18px; accent-color:var(--brand); cursor:pointer; flex:none; }
  .thumb{ position:relative; flex:none; }
  .thumb img{ width:140px; height:79px; object-fit:cover; border-radius:9px; background:#000; display:block; }
  .thumb .dur{
    position:absolute; right:5px; bottom:5px; background:rgba(0,0,0,.82); color:#fff;
    font-size:11px; padding:1px 6px; border-radius:5px; font-variant-numeric:tabular-nums;
  }
  .idx{ position:absolute; left:5px; top:5px; background:rgba(0,0,0,.7); color:#fff;
    font-size:10px; padding:1px 6px; border-radius:5px; }
  .info{ flex:1; min-width:0; }
  .title{ font-size:14px; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .by{ color:var(--muted); font-size:12px; margin-top:2px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .progress{ height:6px; border-radius:6px; background:var(--bg-soft); margin-top:9px; overflow:hidden; }
  .progress > i{ display:block; height:100%; width:0%; border-radius:6px; background:var(--ok); transition:width .3s ease; }
  .progress.busy > i{ background:linear-gradient(90deg,var(--brand),var(--accent));
    background-size:200% 100%; animation:flow 1.3s linear infinite; }
  @keyframes flow{ from{background-position:200% 0;} to{background-position:0 0;} }
  .pill{
    display:inline-flex; align-items:center; gap:6px; font-size:11px; font-weight:600;
    margin-top:7px; padding:2px 9px; border-radius:999px; background:var(--bg-soft); color:var(--muted);
  }
  .pill.done{ color:var(--ok); background:color-mix(in srgb,var(--ok) 14%, transparent); }
  .pill.error{ color:var(--err); background:color-mix(in srgb,var(--err) 14%, transparent); }
  .pill.downloading,.pill.merging{ color:var(--warn); background:color-mix(in srgb,var(--warn) 14%, transparent); }
  .pill.cancelled{ color:var(--faint); }
  .act{ flex:none; display:flex; flex-direction:column; gap:6px; align-items:flex-end; min-width:110px; }

  /* States */
  .err-box{
    display:none; gap:10px; align-items:flex-start; padding:13px 15px; margin-bottom:14px;
    background:color-mix(in srgb,var(--err) 10%, var(--panel)); border:1px solid color-mix(in srgb,var(--err) 35%, var(--border));
    border-radius:var(--radius-sm); color:var(--text); font-size:13px; white-space:pre-wrap;
  }
  .err-box.show{ display:flex; }
  .empty{ text-align:center; color:var(--muted); padding:70px 20px; }
  .empty .big{ font-size:46px; margin-bottom:10px; }
  .empty h2{ margin:0 0 6px; color:var(--text); font-size:18px; }
  .skeleton{ background:var(--panel); border:1px solid var(--border); border-radius:var(--radius); height:103px; overflow:hidden; position:relative; }
  .skeleton::after{ content:""; position:absolute; inset:0;
    background:linear-gradient(90deg,transparent, color-mix(in srgb,var(--text) 6%, transparent), transparent);
    transform:translateX(-100%); animation:shimmer 1.3s infinite; }
  @keyframes shimmer{ to{ transform:translateX(100%); } }

  /* Toasts */
  #toasts{ position:fixed; right:18px; bottom:18px; display:flex; flex-direction:column; gap:8px; z-index:50; }
  .toast{
    background:var(--panel); border:1px solid var(--border); border-left:3px solid var(--brand);
    padding:11px 15px; border-radius:10px; font-size:13px; box-shadow:var(--shadow);
    animation:slidein .25s ease; max-width:320px;
  }
  .toast.ok{ border-left-color:var(--ok); }
  .toast.err{ border-left-color:var(--err); }
  @keyframes slidein{ from{ transform:translateY(10px); opacity:0; } }

  .spin{ display:inline-block; animation:spin 1s linear infinite; }
  @keyframes spin{ to{ transform:rotate(360deg); } }

  @media (max-width:620px){
    .thumb img{ width:104px; height:59px; }
    .act{ min-width:96px; }
    .pl-sub{ display:none; }
  }
</style>
</head>
<body>
<header>
  <div class="wrap head-row">
    <div class="logo">
      <span class="mark">⬇</span>
      <span>YouTube Playlist Downloader<small id="dirline">loading…</small></span>
    </div>
    <span class="grow"></span>
    <a class="ghost-link" href="https://github.com/" target="_blank" rel="noopener" id="ghlink">GitHub</a>
    <button class="icon-btn" id="theme" title="Toggle theme" type="button">🌙</button>
  </div>
</header>

<main class="wrap">
  <div class="search">
    <div class="field">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
      <input id="url" type="text" placeholder="Paste a YouTube playlist or video URL…" autocomplete="off" spellcheck="false">
    </div>
    <select id="quality" title="Download quality">
      <option value="best">Best quality</option>
      <option value="1080">1080p</option>
      <option value="720">720p</option>
      <option value="480">480p</option>
      <option value="audio">Audio only (MP3)</option>
    </select>
    <button id="load" type="button"><span id="load-txt">Load</span></button>
  </div>

  <div id="err" class="err-box"><span>⚠️</span><span id="err-txt"></span></div>

  <div id="panel" hidden>
    <div class="toolbar">
      <div>
        <div class="pl-title" id="pl-title"></div>
        <div class="pl-sub" id="pl-sub"></div>
      </div>
      <span class="grow"></span>
      <label class="chk"><input type="checkbox" id="selall"> Select all</label>
      <div class="field mini-search">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
        <input id="filter" type="text" placeholder="Filter…" autocomplete="off">
      </div>
      <button class="secondary tiny" id="open" type="button">📁 Open folder</button>
      <button class="tiny" id="dlsel" type="button" disabled>⬇ Download selected</button>
      <button class="secondary tiny" id="dlall" type="button">Download all</button>
    </div>

    <div class="overall" id="overall">
      <div class="track"><i id="overall-bar"></i></div>
      <div class="label" id="overall-label"></div>
    </div>

    <div id="list"></div>
  </div>

  <div class="empty" id="empty">
    <div class="big">🎬</div>
    <h2>Paste a playlist to get started</h2>
    <div>Drop in any YouTube playlist or video link above and hit <b>Load</b>.</div>
  </div>
</main>

<div id="toasts"></div>

<script>
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
let videos = [];
const selected = new Set();

/* ---------- helpers ---------- */
function fmtDur(s){
  if(s==null) return "";
  s = Math.round(s); const m = Math.floor(s/60), ss = String(s%60).padStart(2,"0");
  const h = Math.floor(m/60);
  return h>0 ? `${h}:${String(m%60).padStart(2,"0")}:${ss}` : `${m}:${ss}`;
}
function escapeHtml(s){ return (s||"").replace(/[&<>"]/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c])); }

function toast(msg, kind){
  const t = document.createElement("div");
  t.className = "toast" + (kind?(" "+kind):"");
  t.textContent = msg;
  $("#toasts").appendChild(t);
  setTimeout(()=>{ t.style.opacity="0"; t.style.transition="opacity .3s"; setTimeout(()=>t.remove(),300); }, 3200);
}

async function api(path, body){
  const r = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"},
                              body: JSON.stringify(body||{})});
  const data = await r.json();
  if(!r.ok || data.error) throw new Error(data.error || ("HTTP "+r.status));
  return data;
}

/* ---------- rendering ---------- */
function render(){
  const list = $("#list"); list.innerHTML = "";
  videos.forEach((v,i)=>{
    const row = document.createElement("div");
    row.className = "row"; row.id = "v_"+v.id; row.dataset.title = (v.title||"").toLowerCase();
    row.innerHTML = `
      <input class="pick" type="checkbox" data-pick="${v.id}">
      <div class="thumb">
        <span class="idx">${i+1}</span>
        <img loading="lazy" src="${v.thumb}" alt="" onerror="this.style.visibility='hidden'">
        ${v.duration!=null?`<span class="dur">${fmtDur(v.duration)}</span>`:""}
      </div>
      <div class="info">
        <div class="title">${escapeHtml(v.title)}</div>
        <div class="by">${escapeHtml(v.uploader||"")}</div>
        <div class="progress"><i></i></div>
        <div class="pill" data-state>queued</div>
      </div>
      <div class="act">
        <button class="tiny" data-dl="${v.id}">Download</button>
      </div>`;
    list.appendChild(row);
  });

  $$("[data-dl]").forEach(b=> b.onclick = ()=> enqueue([videos.find(v=>v.id===b.dataset.dl)]));
  $$("[data-pick]").forEach(c=> c.onchange = ()=>{
    const id = c.dataset.pick;
    c.checked ? selected.add(id) : selected.delete(id);
    $("#v_"+id).classList.toggle("sel", c.checked);
    syncSelectUI();
  });
  // Reset the per-row pill default text where nothing's been done yet.
  $$("[data-state]").forEach(p=>{ p.textContent="—"; p.className="pill"; });
  applyFilter();
}

function syncSelectUI(){
  $("#dlsel").disabled = selected.size===0;
  $("#dlsel").textContent = selected.size ? `⬇ Download selected (${selected.size})` : "⬇ Download selected";
  const visible = videos.length;
  $("#selall").checked = selected.size>0 && selected.size===visible;
  $("#selall").indeterminate = selected.size>0 && selected.size<visible;
}

function applyFilter(){
  const q = $("#filter").value.trim().toLowerCase();
  videos.forEach(v=>{
    const row = $("#v_"+v.id); if(!row) return;
    row.classList.toggle("hidden", q && !(v.title||"").toLowerCase().includes(q));
  });
}

/* ---------- actions ---------- */
async function load(){
  const url = $("#url").value.trim();
  if(!url){ toast("Paste a URL first", "err"); return; }
  $("#err").classList.remove("show");
  $("#empty").style.display = "none";
  $("#panel").hidden = false;
  $("#load").disabled = true;
  $("#load-txt").innerHTML = '<span class="spin">↻</span> Loading';
  $("#list").innerHTML = Array.from({length:4}, ()=> '<div class="skeleton"></div>').join("");
  $("#pl-title").textContent = "Reading playlist…"; $("#pl-sub").textContent = "";
  try{
    const data = await api("/api/playlist", {url});
    videos = data.videos || [];
    selected.clear();
    $("#pl-title").textContent = data.title || "Playlist";
    $("#pl-sub").textContent = `${videos.length} video${videos.length===1?"":"s"}`;
    if(!videos.length){
      $("#list").innerHTML = `<div class="empty"><div class="big">🤷</div><h2>No videos found</h2></div>`;
    } else {
      render();
    }
    syncSelectUI();
    toast(`Loaded ${videos.length} video${videos.length===1?"":"s"}`, "ok");
  }catch(e){
    $("#panel").hidden = true; $("#empty").style.display = "";
    $("#err").classList.add("show"); $("#err-txt").textContent = "Could not load: " + e.message;
  }finally{
    $("#load").disabled = false; $("#load-txt").textContent = "Load";
  }
}

async function enqueue(vs){
  vs = (vs||[]).filter(Boolean);
  if(!vs.length) return;
  const fmt = $("#quality").value;
  vs.forEach(v=>{
    const p = document.querySelector("#v_"+v.id+" [data-state]");
    if(p){ p.textContent="queued"; p.className="pill"; }
    const btn = document.querySelector("#v_"+v.id+" [data-dl]");
    if(btn) btn.disabled = true;
  });
  try{
    await api("/api/download", {format: fmt, videos: vs.map(v=>({id:v.id,title:v.title,url:v.url}))});
    toast(`Queued ${vs.length} download${vs.length===1?"":"s"}`, "ok");
    $("#overall").classList.add("show");
  }catch(e){ toast("Failed to queue: "+e.message, "err"); }
}

async function cancel(id){
  try{ await api("/api/cancel", {id}); toast("Cancelled", ""); }
  catch(e){ toast("Cancel failed: "+e.message, "err"); }
}

/* ---------- polling ---------- */
function updateOverall(status){
  const states = videos.map(v=> status[v.id]?.state).filter(Boolean);
  const active = states.filter(s=>["queued","downloading","merging"].includes(s)).length;
  const done = states.filter(s=>s==="done").length;
  const total = states.length;
  if(total===0){ $("#overall").classList.remove("show"); return; }
  $("#overall").classList.add("show");
  $("#overall-bar").style.width = (done/total*100) + "%";
  $("#overall-label").textContent =
    active>0 ? `${done}/${total} done · ${active} in progress`
             : `${done}/${total} done`;
}

async function poll(){
  try{
    const data = await api("/api/status", {});
    const status = data.status || {};
    Object.values(status).forEach(s=>{
      const row = document.querySelector("#v_"+s.vid); if(!row) return;
      const bar = row.querySelector(".progress > i");
      const prog = row.querySelector(".progress");
      bar.style.width = (s.percent||0) + "%";
      prog.classList.toggle("busy", s.state==="downloading" || s.state==="merging");

      const pill = row.querySelector("[data-state]");
      let txt = s.state;
      if(s.state==="downloading") txt = `↓ ${Math.round(s.percent||0)}% · ${s.speed||""} · ETA ${s.eta||""}`;
      else if(s.state==="merging") txt = "merging…";
      else if(s.state==="done") txt = "✓ done";
      else if(s.state==="error") txt = "✕ " + (s.error||"error");
      else if(s.state==="cancelled") txt = "cancelled";
      else if(s.state==="queued") txt = "• queued";
      pill.textContent = txt; pill.className = "pill " + s.state;

      const busy = ["downloading","merging","queued"].includes(s.state);
      const act = row.querySelector(".act");
      if(busy){
        act.innerHTML = `<button class="secondary tiny" data-cancel="${s.vid}">Cancel</button>`;
        act.querySelector("[data-cancel]").onclick = ()=> cancel(s.vid);
      } else if(act.querySelector("[data-cancel]") || !act.querySelector("[data-dl]")){
        const label = s.state==="done" ? "Re-download" : "Download";
        act.innerHTML = `<button class="tiny ${s.state==='done'?'secondary':''}" data-dl="${s.vid}">${label}</button>`;
        act.querySelector("[data-dl]").onclick = ()=> enqueue([videos.find(v=>v.id===s.vid)]);
      }
    });
    updateOverall(status);
  }catch(e){ /* ignore transient poll errors */ }
}

/* ---------- theme ---------- */
function setTheme(t){
  document.documentElement.setAttribute("data-theme", t);
  $("#theme").textContent = t==="light" ? "☀️" : "🌙";
  try{ localStorage.setItem("ytdl-theme", t); }catch(e){}
}
(function initTheme(){
  let t; try{ t = localStorage.getItem("ytdl-theme"); }catch(e){}
  if(!t) t = matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  setTheme(t);
})();

/* ---------- wire up ---------- */
$("#load").onclick = load;
$("#url").addEventListener("keydown", e=>{ if(e.key==="Enter") load(); });
$("#dlall").onclick = ()=> enqueue(videos);
$("#dlsel").onclick = ()=> enqueue(videos.filter(v=>selected.has(v.id)));
$("#open").onclick = ()=> api("/api/open", {}).catch(()=> toast("Could not open folder","err"));
$("#filter").addEventListener("input", applyFilter);
$("#theme").onclick = ()=> setTheme(document.documentElement.getAttribute("data-theme")==="light"?"dark":"light");
$("#selall").onchange = e=>{
  selected.clear();
  if(e.target.checked) videos.forEach(v=> selected.add(v.id));
  $$("[data-pick]").forEach(c=>{ c.checked = e.target.checked; $("#v_"+c.dataset.pick).classList.toggle("sel", e.target.checked); });
  syncSelectUI();
};
fetch("/api/info").then(r=>r.json()).then(d=>{ $("#dirline").textContent = "Saving to " + d.dir; });
setInterval(poll, 1000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quieter console
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj))

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML, "text/html; charset=utf-8")
        elif self.path == "/api/info":
            self._json(200, {"dir": DOWNLOAD_DIR})
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        try:
            if self.path == "/api/playlist":
                body = self._read_json()
                title, videos = list_playlist((body.get("url") or "").strip())
                self._json(200, {"title": title, "videos": videos})
            elif self.path == "/api/download":
                body = self._read_json()
                fmt = body.get("format", "best")
                for v in body.get("videos", []):
                    vid = v.get("id")
                    if not vid:
                        continue
                    _meta[vid] = {"title": v.get("title", ""),
                                  "url": v.get("url", ""), "format": fmt}
                    _cancelled.discard(vid)
                    set_status(vid, state="queued", title=v.get("title", ""),
                               percent=0, error="")
                    _dlqueue.put(vid)
                self._json(200, {"ok": True})
            elif self.path == "/api/status":
                with _lock:
                    self._json(200, {"status": _status})
            elif self.path == "/api/cancel":
                body = self._read_json()
                vid = (body.get("id") or "").strip()
                if vid:
                    cancel_download(vid)
                self._json(200, {"ok": True})
            elif self.path == "/api/open":
                open_folder()
                self._json(200, {"ok": True})
            else:
                self._json(404, {"error": "not found"})
        except Exception as e:  # noqa: BLE001
            self._json(500, {"error": str(e)})


def main():
    if not YTDLP:
        raise SystemExit(
            "yt-dlp not found on PATH. Install it first "
            "(e.g. `brew install yt-dlp` or `pip install yt-dlp`)."
        )
    if not FFMPEG:
        print("WARNING: ffmpeg not found — merging video+audio will fail.")
    print(f"yt-dlp:    {YTDLP}")
    print(f"downloads: {DOWNLOAD_DIR}")
    print(f"serving:   http://{HOST}:{PORT}  (Ctrl+C to stop)")
    try:
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nbye 👋")


if __name__ == "__main__":
    main()
