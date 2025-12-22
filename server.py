import json
import sqlite3
import os
import secrets
import subprocess
import tempfile
import threading
import time
import uuid
import hmac
import hashlib
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import qrcode
import requests
from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI, File, Header, HTTPException, Query, Response, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from biliurl import getCid

app = FastAPI(title="biliurl http server", version="0.2.0")

BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Origin": "https://www.bilibili.com",
}

# qn mapping (common values)
Q480 = 32
QMAX = 125

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_DIR = os.path.join(ROOT_DIR, "cookies")

DB_FILE = os.path.join(ROOT_DIR, "store.db")

# Root-level encrypted secret key (used for both session encryption and user_id keyed lookup)
SESSIONS_KEY_FILE = os.path.join(ROOT_DIR, "sessions.key")

# Concurrency safety (threaded requests / sync endpoints)
STORE_LOCK = threading.RLock()


@dataclass
class UserSession:
    created_at: float
    token: str
    cookie_dict: Dict[str, str]


USER_SESSIONS: Dict[str, UserSession] = {}


def _now() -> float:
    return time.time()


def _ensure_dirs() -> None:
    os.makedirs(COOKIES_DIR, exist_ok=True)


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, timeout=30, isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def _db_init() -> None:
    _ensure_dirs()
    conn = _db_connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS login_flows (
                login_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                qrcode_key TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                user_key TEXT PRIMARY KEY,
                payload BLOB NOT NULL
            );
            """
        )
    finally:
        conn.close()


def _atomic_write_bytes(path: str, data: bytes) -> None:
    tmp_dir = os.path.dirname(os.path.abspath(path)) or "."
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=tmp_dir) as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
        tmp_path = f.name
    os.replace(tmp_path, path)


def _atomic_write_text(path: str, text: str) -> None:
    _atomic_write_bytes(path, text.encode("utf-8"))


def _load_or_create_key() -> bytes:
    if os.path.exists(SESSIONS_KEY_FILE):
        with open(SESSIONS_KEY_FILE, "rb") as f:
            key = f.read().strip()
        _ = Fernet(key)
        return key

    key = Fernet.generate_key()
    _atomic_write_bytes(SESSIONS_KEY_FILE, key + b"\n")
    return key


def _fernet() -> Fernet:
    return Fernet(_load_or_create_key())


def _user_key(user_id: str) -> str:
    # Deterministic keyed hash so DB doesn't store plaintext user_id
    secret = _load_or_create_key()
    return hmac.new(secret, user_id.encode("utf-8"), hashlib.sha256).hexdigest()


def _encrypt_json(obj: Dict[str, Any]) -> bytes:
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _fernet().encrypt(raw)


def _decrypt_json(blob: bytes) -> Dict[str, Any]:
    raw = _fernet().decrypt(blob)
    return json.loads(raw.decode("utf-8"))


def _cookie_path(user_id: str) -> str:
    # 按需求：文件名就是 user_id（无扩展名）
    return os.path.join(COOKIES_DIR, user_id)


def _save_cookies_to_disk(user_id: str, cookie_dict: Dict[str, str]) -> None:
    _ensure_dirs()
    _atomic_write_text(_cookie_path(user_id), json.dumps(cookie_dict, ensure_ascii=False, indent=2))


def _load_cookies_from_disk(user_id: str) -> Optional[Dict[str, str]]:
    path = _cookie_path(user_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _cleanup_login_flows(ttl_seconds: int = 600) -> None:
    cutoff = _now() - ttl_seconds

    conn = _db_connect()
    try:
        conn.execute("DELETE FROM login_flows WHERE created_at < ?", (cutoff,))
    finally:
        conn.close()


def _make_qr_png_bytes(text: str) -> bytes:
    img = qrcode.make(text)
    # Pillow image -> bytes
    from io import BytesIO

    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _bili_qr_generate(sess: requests.Session) -> Tuple[str, str]:
    url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    resp = sess.get(url, headers=BILI_HEADERS, timeout=15)
    data = resp.json()
    if data.get("code") != 0 or not data.get("data"):
        raise RuntimeError(f"QR generate failed: {data}")
    qrcode_key = data["data"]["qrcode_key"]
    qr_url = data["data"]["url"]
    return qrcode_key, qr_url


def _bili_qr_poll(sess: requests.Session, qrcode_key: str) -> Dict[str, Any]:
    url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
    resp = sess.get(url, params={"qrcode_key": qrcode_key}, headers=BILI_HEADERS, timeout=15)
    return resp.json()


def _bili_qr_poll_stateless(qrcode_key: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """多进程友好的轮询：不依赖 generate 阶段的 Session；成功时从响应里拿到 Set-Cookie。"""
    url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
    resp = requests.get(url, params={"qrcode_key": qrcode_key}, headers=BILI_HEADERS, timeout=15)
    data = resp.json()
    cookie_dict = {k: v for k, v in resp.cookies.get_dict().items()}
    return data, cookie_dict


def _extract_cookies(sess: requests.Session) -> Dict[str, str]:
    return {k: v for k, v in sess.cookies.get_dict().items()}


def _get_auth_from_request(
    user_id_q: Optional[str],
    token_q: Optional[str],
    user_id_h: Optional[str],
    token_h: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    user_id = user_id_q or user_id_h
    token = token_q or token_h
    return user_id, token


def _validate_user(user_id: Optional[str], token: Optional[str]) -> Optional[UserSession]:
    if not user_id or not token:
        return None

    with STORE_LOCK:
        sess = USER_SESSIONS.get(user_id)

    # 允许并发/重启后继续使用：内存没有就从磁盘恢复
    if not sess:
        user_key = _user_key(user_id)
        conn = _db_connect()
        try:
            row = conn.execute("SELECT payload FROM sessions WHERE user_key = ?", (user_key,)).fetchone()
        finally:
            conn.close()

        if row and row[0]:
            try:
                payload = _decrypt_json(row[0])
            except InvalidToken:
                payload = None

            if isinstance(payload, dict) and payload.get("token"):
                cookie_dict = _load_cookies_from_disk(user_id)
                if cookie_dict:
                    sess = UserSession(
                        created_at=float(payload.get("created_at") or _now()),
                        token=str(payload["token"]),
                        cookie_dict=cookie_dict,
                    )
                    with STORE_LOCK:
                        USER_SESSIONS[user_id] = sess

    if not sess:
        return None
    if secrets.compare_digest(sess.token, token):
        return sess
    return None


def _playurl_json(bvid: str, cid: str, qn: int, cookies: Optional[Dict[str, str]]) -> Dict[str, Any]:
    base_params = {
        "from_client": "BROWSER",
        "cid": cid,
        "qn": qn,
        "fourk": 1,
        "fnver": 0,
        "fnval": 4048,
        "bvid": bvid,
    }

    # Try wbi first, then fallback.
    urls = [
        "https://api.bilibili.com/x/player/wbi/playurl",
        "https://api.bilibili.com/x/player/playurl",
    ]

    last: Optional[Dict[str, Any]] = None
    for url in urls:
        r = requests.get(url, params=base_params, headers=BILI_HEADERS, cookies=cookies, timeout=15)
        j = r.json()
        last = j
        if j.get("code") == 0 and j.get("data") and j["data"].get("dash"):
            return j

    raise HTTPException(status_code=502, detail={"error": "bilibili_playurl_failed", "raw": last})


def _playurl_dash_with_fallback(
    bvid: str,
    cid: str,
    cookies: Optional[Dict[str, str]],
    authed: bool,
) -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, str]], bool, int]:
    """获取 playurl(dash) 并在鉴权无效/失效时自动降级到游客 480p。

    返回：(playurl_json, dash, effective_cookies, effective_authed, effective_qn)
    """

    qn = QMAX if authed else Q480
    try:
        j = _playurl_json(bvid=bvid, cid=cid, qn=qn, cookies=cookies)
        dash = j["data"]["dash"]
        return j, dash, cookies, authed, qn
    except HTTPException as e:
        # 如果带登录态失败，则自动降级为游客 480p
        if authed:
            try:
                j2 = _playurl_json(bvid=bvid, cid=cid, qn=Q480, cookies=None)
                dash2 = j2["data"]["dash"]
                return j2, dash2, None, False, Q480
            except HTTPException:
                raise e
        raise


def _auth_cookies_and_qn(
    user_id: Optional[str],
    token: Optional[str],
    x_user_id: Optional[str],
    x_token: Optional[str],
) -> Tuple[Optional[Dict[str, str]], int, bool]:
    uid, tok = _get_auth_from_request(user_id, token, x_user_id, x_token)
    user_sess = _validate_user(uid, tok)
    cookies = user_sess.cookie_dict if user_sess else None
    qn = QMAX if user_sess else Q480
    return cookies, qn, bool(user_sess)


def _stream_download(url: str, cookies: Optional[Dict[str, str]]):
    headers = dict(BILI_HEADERS)
    headers["Accept-Encoding"] = "identity"
    upstream = requests.get(url, headers=headers, cookies=cookies, stream=True, timeout=30)
    upstream.raise_for_status()

    def _iter():
        try:
            for chunk in upstream.iter_content(chunk_size=1024 * 256):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    content_type = upstream.headers.get("Content-Type") or "application/octet-stream"
    return _iter(), content_type


def _download_to_file(url: str, cookies: Optional[Dict[str, str]], file_path: str) -> None:
    headers = dict(BILI_HEADERS)
    headers["Accept-Encoding"] = "identity"
    r = requests.get(url, headers=headers, cookies=cookies, stream=True, timeout=30)
    r.raise_for_status()
    with open(file_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 256):
            if chunk:
                f.write(chunk)
    r.close()


def _ffmpeg_mux_to_mp4(video_path: str, audio_path: str, output_path: str) -> None:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "ffmpeg_not_available", "message": str(e)})

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        output_path,
    ]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "ffmpeg_mux_failed",
                "returncode": p.returncode,
                "stderr": (p.stderr or "")[-4000:],
            },
        )


def _pick_video_audio(
    dash: Dict[str, Any],
    prefer_video_id: Optional[int] = None,
    max_video_id: Optional[int] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    videos = dash.get("video") or []
    audios = dash.get("audio") or []
    if not videos or not audios:
        raise HTTPException(status_code=502, detail={"error": "dash_missing"})

    def vid_id(x: Dict[str, Any]) -> int:
        try:
            return int(x.get("id") or 0)
        except Exception:
            return 0

    video_candidates = list(videos)
    if max_video_id is not None:
        capped = [v for v in video_candidates if vid_id(v) <= max_video_id]
        if capped:
            video_candidates = capped
        else:
            # 如果服务端只返回了更高画质，兜底选择最低画质，避免无鉴权时拿到更高画质
            video_candidates = [min(videos, key=vid_id)]
    if prefer_video_id is not None:
        for v in video_candidates:
            if vid_id(v) == prefer_video_id:
                best_video = v
                break
        else:
            best_video = max(video_candidates, key=vid_id)
    else:
        best_video = max(video_candidates, key=vid_id)

    best_audio = max(audios, key=vid_id)
    return best_video, best_audio


@app.get("/login/qr", responses={200: {"content": {"image/png": {}}}})
def login_qr():
    """返回二维码图片（image/png）。登录流程 id 放在响应头 X-Login-Id。"""
    _cleanup_login_flows()
    _ensure_dirs()
    _ = _load_or_create_key()

    _db_init()

    sess = requests.Session()
    qrcode_key, qr_url = _bili_qr_generate(sess)
    png = _make_qr_png_bytes(qr_url)

    login_id = uuid.uuid4().hex
    conn = _db_connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO login_flows(login_id, created_at, qrcode_key) VALUES (?, ?, ?)",
            (login_id, _now(), qrcode_key),
        )
    finally:
        conn.close()

    resp = Response(content=png, media_type="image/png")
    resp.headers["X-Login-Id"] = login_id
    return resp


@app.get("/", response_class=HTMLResponse)
def index():
        """简易测试页：扫码登录 -> 获取直链 -> 分别下载视频/音频。"""
        return HTMLResponse(
                """<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>biliurl 测试页</title>
    <style>
        body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }
        .row { display: flex; gap: 24px; flex-wrap: wrap; align-items: flex-start; }
        .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px; min-width: 320px; }
        label { display: block; margin: 8px 0 4px; }
        input { width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 8px 12px; margin-top: 8px; }
        pre { background: #f7f7f7; padding: 12px; overflow: auto; }
        img { max-width: 280px; border: 1px solid #eee; }
        .muted { color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <h2>biliurl 业务测试页</h2>
    <div class="row">
        <div class="card">
            <h3>1) 扫码登录</h3>
            <button id="btnQr">获取二维码</button>
            <div class="muted">获取后请用 B 站 App 扫码并确认</div>
            <div style="margin-top:12px;"><img id="qrImg" alt="二维码" /></div>
            <div class="muted" style="margin-top:8px;">login_id: <span id="loginId">-</span></div>
            <button id="btnPoll" disabled>开始轮询登录状态</button>
            <pre id="loginOut">{}</pre>
        </div>

        <div class="card">
            <h3>2) 获取直链</h3>
            <label>BVID</label>
            <input id="bvid" placeholder="例如：BV1HfK3zPEHE" />
            <div class="muted">无 user_id/token：返回 480p；有则返回最高画质</div>
            <button id="btnUrls">获取视频/音频直链</button>
            <pre id="urlOut">{}</pre>
        </div>

        <div class="card">
            <h3>3) 分别下载</h3>
            <div class="muted">这里使用服务端转发下载，避免直链跨域/防盗链问题</div>
            <button id="btnDlVideo">下载视频</button>
            <button id="btnDlAudio">下载音频</button>
            <hr style="margin: 12px 0; border: 0; border-top: 1px solid #eee;" />
            <h4 style="margin: 0 0 8px;">4) 服务端下载并合并 MP4</h4>
            <div class="muted">服务端自动拉取 video/audio 流并用 ffmpeg 合并封装（无需先下载再上传）</div>
            <button id="btnMergeRemote">下载并合并 MP4</button>
            <pre id="dlOut">{}</pre>
        </div>
    </div>

<script>
let loginId = null;
let userId = null;
let token = null;
let pollTimer = null;

function $(id){ return document.getElementById(id); }
function setJson(id, obj){ $(id).textContent = JSON.stringify(obj, null, 2); }

async function getQr(){
    const r = await fetch('/login/qr');
    if(!r.ok) throw new Error('获取二维码失败: ' + r.status);
    loginId = r.headers.get('X-Login-Id');
    $('loginId').textContent = loginId || '-';
    const blob = await r.blob();
    $('qrImg').src = URL.createObjectURL(blob);
    $('btnPoll').disabled = !loginId;
    setJson('loginOut', {status:'qr_ready', login_id: loginId});
}

async function pollLoginOnce(){
    if(!loginId) return;
    const r = await fetch('/login/status?login_id=' + encodeURIComponent(loginId));
    const j = await r.json();
    setJson('loginOut', j);
    if(j.status === 'success'){
        userId = j.user_id;
        token = j.token;
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

function startPoll(){
    if(pollTimer) return;
    pollLoginOnce();
    pollTimer = setInterval(pollLoginOnce, 2000);
}

function authQuery(){
    if(userId && token) return '&user_id=' + encodeURIComponent(userId) + '&token=' + encodeURIComponent(token);
    return '';
}

async function getUrls(){
    const bvid = $('bvid').value.trim();
    if(!bvid) throw new Error('请填写 bvid');
    const v = await fetch('/stream/video?bvid=' + encodeURIComponent(bvid) + authQuery());
    const a = await fetch('/stream/audio?bvid=' + encodeURIComponent(bvid) + authQuery());
    const jv = await v.json();
    const ja = await a.json();
    setJson('urlOut', {video: jv, audio: ja, auth: Boolean(userId && token)});
}

function download(kind){
    const bvid = $('bvid').value.trim();
    if(!bvid) throw new Error('请填写 bvid');
    const url = '/download/' + kind + '?bvid=' + encodeURIComponent(bvid) + authQuery();
    window.location.href = url;
    setJson('dlOut', {action: 'download', url});
}

function mergeRemote(){
    const bvid = $('bvid').value.trim();
    if(!bvid) throw new Error('请填写 bvid');
    const url = '/merge/mp4/remote?bvid=' + encodeURIComponent(bvid) + authQuery();
    window.location.href = url;
    setJson('dlOut', {action: 'merge_remote_download', url});
}

$('btnQr').addEventListener('click', async ()=>{ try{ await getQr(); } catch(e){ setJson('loginOut', {error: String(e)}); } });
$('btnPoll').addEventListener('click', async ()=>{ try{ startPoll(); } catch(e){ setJson('loginOut', {error: String(e)}); } });
$('btnUrls').addEventListener('click', async ()=>{ try{ await getUrls(); } catch(e){ setJson('urlOut', {error: String(e)}); } });
$('btnDlVideo').addEventListener('click', ()=>{ try{ download('video'); } catch(e){ setJson('dlOut', {error: String(e)}); } });
$('btnDlAudio').addEventListener('click', ()=>{ try{ download('audio'); } catch(e){ setJson('dlOut', {error: String(e)}); } });
$('btnMergeRemote').addEventListener('click', ()=>{ try{ mergeRemote(); } catch(e){ setJson('dlOut', {error: String(e)}); } });
</script>
</body>
</html>"""
        )


@app.get("/login/status")
def login_status(login_id: str = Query(...)):
    """轮询登录状态。成功时返回 user_id + token（并持久化 cookies 与 user/token）。"""
    _cleanup_login_flows()

    conn = _db_connect()
    try:
        row = conn.execute("SELECT qrcode_key FROM login_flows WHERE login_id = ?", (login_id,)).fetchone()
    finally:
        conn.close()

    if not row or not row[0]:
        raise HTTPException(status_code=404, detail={"error": "login_id_not_found"})

    qrcode_key = str(row[0])
    data, cookie_dict_from_poll = _bili_qr_poll_stateless(qrcode_key)
    d = (data or {}).get("data") or {}
    code = d.get("code")

    # 0: 成功, 86038: 二维码失效, 86101: 未扫码, 86090: 已扫码未确认
    if code == 86101:
        return {"status": "waiting"}
    if code == 86090:
        return {"status": "scanned"}
    if code == 86038:
        return {"status": "expired"}

    if code == 0:
        # 多进程下不依赖 Session，直接取 poll 响应里的 cookies
        cookie_dict = cookie_dict_from_poll
        if not cookie_dict:
            raise HTTPException(status_code=502, detail={"error": "login_success_but_no_cookies", "raw": data})

        user_id = uuid.uuid4().hex
        token = secrets.token_urlsafe(32)

        _save_cookies_to_disk(user_id, cookie_dict)

        payload = {"user_id": user_id, "token": token, "created_at": _now()}
        enc = _encrypt_json(payload)
        user_key = _user_key(user_id)

        conn = _db_connect()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO sessions(user_key, payload) VALUES (?, ?)",
                (user_key, enc),
            )
            conn.execute("DELETE FROM login_flows WHERE login_id = ?", (login_id,))
        finally:
            conn.close()

        with STORE_LOCK:
            USER_SESSIONS[user_id] = UserSession(created_at=_now(), token=token, cookie_dict=cookie_dict)

        return {"status": "success", "user_id": user_id, "token": token}

    return {"status": "unknown", "raw": data}


@app.get("/download/video")
def download_video(
    bvid: str = Query(...),
    user_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_token: Optional[str] = Header(default=None, alias="X-Token"),
):
    """服务端转发下载视频流（单独视频轨道 m4s）。"""
    cookies, _qn, authed = _auth_cookies_and_qn(user_id, token, x_user_id, x_token)
    cid = getCid(bvid, cookies=cookies)
    _j, dash, cookies_eff, authed_eff, _qn_eff = _playurl_dash_with_fallback(
        bvid=bvid, cid=cid, cookies=cookies, authed=authed
    )
    prefer = Q480 if not authed else None
    max_id = Q480 if not authed else None
    prefer = Q480 if not authed_eff else None
    max_id = Q480 if not authed_eff else None
    best_video, _best_audio = _pick_video_audio(dash, prefer_video_id=prefer, max_video_id=max_id)
    url = best_video.get("baseUrl")
    if not url:
        raise HTTPException(status_code=502, detail={"error": "no_video_url"})

    iterator, content_type = _stream_download(url, cookies_eff)
    filename = f"video-{bvid}-id{best_video.get('id')}.m4s"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iterator, media_type=content_type, headers=headers)


@app.get("/download/audio")
def download_audio(
    bvid: str = Query(...),
    user_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_token: Optional[str] = Header(default=None, alias="X-Token"),
):
    """服务端转发下载音频流（单独音频轨道 m4s）。"""
    cookies, _qn, authed = _auth_cookies_and_qn(user_id, token, x_user_id, x_token)
    cid = getCid(bvid, cookies=cookies)
    _j, dash, cookies_eff, _authed_eff, _qn_eff = _playurl_dash_with_fallback(
        bvid=bvid, cid=cid, cookies=cookies, authed=authed
    )
    _best_video, best_audio = _pick_video_audio(dash)
    url = best_audio.get("baseUrl")
    if not url:
        raise HTTPException(status_code=502, detail={"error": "no_audio_url"})

    iterator, content_type = _stream_download(url, cookies_eff)
    filename = f"audio-{bvid}.m4s"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iterator, media_type=content_type, headers=headers)


@app.post("/merge/mp4")
def merge_mp4(
    bvid: str = Query("output"),
    video_file: UploadFile = File(...),
    audio_file: UploadFile = File(...),
):
    """上传 video.m4s + audio.m4s，在服务端用 ffmpeg 封装合并成 mp4 并返回下载。"""

    tmp_dir = tempfile.mkdtemp(prefix="mux_")
    video_path = os.path.join(tmp_dir, "video.m4s")
    audio_path = os.path.join(tmp_dir, "audio.m4s")
    out_path = os.path.join(tmp_dir, "merged.mp4")

    try:
        with open(video_path, "wb") as f:
            while True:
                chunk = video_file.file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        with open(audio_path, "wb") as f:
            while True:
                chunk = audio_file.file.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        _ffmpeg_mux_to_mp4(video_path, audio_path, out_path)

        def _iter_mp4():
            try:
                with open(out_path, "rb") as f:
                    while True:
                        buf = f.read(1024 * 256)
                        if not buf:
                            break
                        yield buf
            finally:
                try:
                    video_file.file.close()
                except Exception:
                    pass
                try:
                    audio_file.file.close()
                except Exception:
                    pass
                try:
                    for p in (video_path, audio_path, out_path):
                        if os.path.exists(p):
                            os.remove(p)
                    if os.path.isdir(tmp_dir):
                        os.rmdir(tmp_dir)
                except Exception:
                    pass

        safe_name = "".join([c for c in bvid if c.isalnum() or c in ("-", "_", ".")]) or "output"
        headers = {"Content-Disposition": f'attachment; filename="{safe_name}.mp4"'}
        return StreamingResponse(_iter_mp4(), media_type="video/mp4", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        # Cleanup on unexpected error
        try:
            video_file.file.close()
        except Exception:
            pass
        try:
            audio_file.file.close()
        except Exception:
            pass
        try:
            for p in (video_path, audio_path, out_path):
                if os.path.exists(p):
                    os.remove(p)
            if os.path.isdir(tmp_dir):
                os.rmdir(tmp_dir)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail={"error": "merge_failed", "message": str(e)})


@app.get("/merge/mp4/remote")
def merge_mp4_remote(
    bvid: str = Query(...),
    user_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_token: Optional[str] = Header(default=None, alias="X-Token"),
):
    """服务端根据 bvid 拉取 video.m4s + audio.m4s，并用 ffmpeg 合并成 mp4 返回下载。"""

    cookies, _qn, authed = _auth_cookies_and_qn(user_id, token, x_user_id, x_token)
    cid = getCid(bvid, cookies=cookies)
    _j, dash, cookies_eff, authed_eff, _qn_eff = _playurl_dash_with_fallback(
        bvid=bvid, cid=cid, cookies=cookies, authed=authed
    )

    prefer = Q480 if not authed_eff else None
    max_id = Q480 if not authed_eff else None
    best_video, best_audio = _pick_video_audio(dash, prefer_video_id=prefer, max_video_id=max_id)

    video_url = best_video.get("baseUrl")
    audio_url = best_audio.get("baseUrl")
    if not video_url or not audio_url:
        raise HTTPException(status_code=502, detail={"error": "no_stream_url"})

    tmp_dir = tempfile.mkdtemp(prefix="mux_remote_")
    video_path = os.path.join(tmp_dir, "video.m4s")
    audio_path = os.path.join(tmp_dir, "audio.m4s")
    out_path = os.path.join(tmp_dir, "merged.mp4")

    try:
        _download_to_file(video_url, cookies_eff, video_path)
        _download_to_file(audio_url, cookies_eff, audio_path)
        _ffmpeg_mux_to_mp4(video_path, audio_path, out_path)

        def _iter_mp4():
            try:
                with open(out_path, "rb") as f:
                    while True:
                        buf = f.read(1024 * 256)
                        if not buf:
                            break
                        yield buf
            finally:
                try:
                    for p in (video_path, audio_path, out_path):
                        if os.path.exists(p):
                            os.remove(p)
                    if os.path.isdir(tmp_dir):
                        os.rmdir(tmp_dir)
                except Exception:
                    pass

        safe_name = "".join([c for c in bvid if c.isalnum() or c in ("-", "_", ".")]) or "output"
        filename = f"merged-{safe_name}.mp4"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(_iter_mp4(), media_type="video/mp4", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        try:
            for p in (video_path, audio_path, out_path):
                if os.path.exists(p):
                    os.remove(p)
            if os.path.isdir(tmp_dir):
                os.rmdir(tmp_dir)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail={"error": "merge_remote_failed", "message": str(e)})


@app.get("/stream/video")
def stream_video(
    bvid: str = Query(...),
    user_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_token: Optional[str] = Header(default=None, alias="X-Token"),
):
    """返回视频直链。未提供/无效鉴权时固定 480p；提供有效鉴权时返回最高可用。"""
    _cleanup_login_flows()

    uid, tok = _get_auth_from_request(user_id, token, x_user_id, x_token)
    user_sess = _validate_user(uid, tok)

    cookies = user_sess.cookie_dict if user_sess else None
    authed = bool(user_sess)

    cid = getCid(bvid, cookies=cookies)
    _j, dash, _cookies_eff, authed_eff, qn_eff = _playurl_dash_with_fallback(
        bvid=bvid, cid=cid, cookies=cookies, authed=authed
    )

    prefer = Q480 if not authed_eff else None
    max_id = Q480 if not authed_eff else None
    best_video, _best_audio = _pick_video_audio(dash, prefer_video_id=prefer, max_video_id=max_id)

    return {
        "bvid": bvid,
        "cid": cid,
        "auth": bool(authed_eff),
        "qn_request": qn_eff,
        "qn_selected": best_video.get("id"),
        "url": best_video.get("baseUrl"),
        "backup_url": (best_video.get("backupUrl") or []),
    }


@app.get("/stream/audio")
def stream_audio(
    bvid: str = Query(...),
    user_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_token: Optional[str] = Header(default=None, alias="X-Token"),
):
    """返回音频直链。未提供/无效鉴权时用游客（无 cookie）；提供有效鉴权时用登录 cookie。"""
    _cleanup_login_flows()

    uid, tok = _get_auth_from_request(user_id, token, x_user_id, x_token)
    user_sess = _validate_user(uid, tok)

    cookies = user_sess.cookie_dict if user_sess else None
    authed = bool(user_sess)

    cid = getCid(bvid, cookies=cookies)
    _j, dash, _cookies_eff, authed_eff, qn_eff = _playurl_dash_with_fallback(
        bvid=bvid, cid=cid, cookies=cookies, authed=authed
    )

    _best_video, best_audio = _pick_video_audio(dash)

    return {
        "bvid": bvid,
        "cid": cid,
        "auth": bool(authed_eff),
        "qn_request": qn_eff,
        "url": best_audio.get("baseUrl"),
        "backup_url": (best_audio.get("backupUrl") or []),
    }
