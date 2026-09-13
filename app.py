from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "DiskWala Downloader Backend",
        "status": "online"
    })

@app.get("/health")
def health():
    return jsonify({"ok": True, "status": "healthy"})

@app.post("/api/download")
def download():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()

    if not url:
        return jsonify({"ok": False, "error": "URL is required"}), 400

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return jsonify({
            "ok": False,
            "error": "Please provide a valid http/https URL"
        }), 400

    # Test response only. The actual authorized downloader provider
    # will be connected after the backend connection is verified.
    return jsonify({
        "ok": True,
        "status": "received",
        "message": "Link received successfully. Downloader provider is not connected yet.",
        "url": url
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
