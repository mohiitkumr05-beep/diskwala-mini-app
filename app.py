from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json
from urllib.parse import urlparse, unquote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

app = Flask(__name__)
CORS(app)

API_URL = os.environ.get("DISKWALA_API_URL", "https://diskwaladevapi.in/api/v1/diskwala/extract")
API_KEY = os.environ.get("DISKWALA_API_KEY", "")
ALLOWED_HOSTS = {"diskwala.com", "www.diskwala.com"}

def valid_url(url):
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and (p.hostname or "").lower() in ALLOWED_HOSTS
    except Exception:
        return False

def find(data, keys):
    if isinstance(data, dict):
        for k in keys:
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v
        for v in data.values():
            r = find(v, keys)
            if r:
                return r
    elif isinstance(data, list):
        for v in data:
            r = find(v, keys)
            if r:
                return r
    return None

def find_number(data, keys):
    if isinstance(data, dict):
        for k in keys:
            v = data.get(k)
            if isinstance(v, (int, float)) or (isinstance(v, str) and v):
                return v
        for v in data.values():
            r = find_number(v, keys)
            if r is not None:
                return r
    elif isinstance(data, list):
        for v in data:
            r = find_number(v, keys)
            if r is not None:
                return r
    return None

def filename(url):
    try:
        n = unquote(urlparse(url).path.rstrip("/").split("/")[-1])
        return n or "DiskWala_File"
    except Exception:
        return "DiskWala_File"

def provider_call(url):
    body = json.dumps({"url": url}).encode()
    req = Request(API_URL, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": API_KEY,
        "User-Agent": "DiskWala-Mini-App/1.0"
    }, method="POST")
    try:
        with urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8", errors="replace")
            try:
                return r.status, json.loads(raw)
            except json.JSONDecodeError:
                return r.status, {"raw_response": raw}
    except HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"error": raw or str(e)}
    except URLError as e:
        raise RuntimeError(f"Provider connection failed: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"Provider request failed: {e}")

@app.get("/")
def home():
    return jsonify({"ok": True, "service": "DiskWala Downloader Backend",
                    "status": "online", "api_configured": bool(API_KEY)})

@app.get("/health")
def health():
    return jsonify({"ok": True, "status": "healthy",
                    "api_configured": bool(API_KEY)})

@app.post("/api/download")
def download():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()

    if not url:
        return jsonify({"ok": False, "error": "Please enter a DiskWala link."}), 400
    if not valid_url(url):
        return jsonify({"ok": False, "error": "Please enter a valid DiskWala URL."}), 400
    if not API_KEY:
        return jsonify({"ok": False, "error": "DISKWALA_API_KEY is not configured on Render."}), 500

    try:
        status, result = provider_call(url)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    if status >= 400:
        msg = find(result, ["message", "error", "detail", "error_message"])
        return jsonify({"ok": False, "error": msg or "The DiskWala API rejected the request.",
                        "provider_status": status}), 502

    download_url = find(result, [
        "direct_link", "download_url", "downloadLink", "direct_url", "directUrl",
        "file_url", "fileUrl", "media_url", "mediaUrl", "url"
    ])
    stream_url = find(result, [
        "m3u8_url", "m3u8", "stream_url", "streamUrl",
        "streaming_url", "play_url", "playUrl"
    ])
    thumbnail = find(result, [
        "thumbnail", "thumbnail_url", "thumbnailUrl", "thumb",
        "cover", "cover_url", "poster"
    ])
    name = find(result, ["filename", "file_name", "fileName", "name", "title"])
    size = find_number(result, ["size", "file_size", "fileSize", "size_bytes", "sizeBytes"])

    if not download_url and not stream_url:
        return jsonify({
            "ok": False,
            "error": "The API responded successfully, but no media URL was found.",
            "provider_status": status,
            "provider_response": result
        }), 502

    media = download_url or stream_url
    return jsonify({
        "ok": True, "status": "success",
        "filename": name or filename(media),
        "size": size,
        "download_url": download_url,
        "stream_url": stream_url or download_url,
        "thumbnail": thumbnail,
        "message": "File extracted successfully."
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
