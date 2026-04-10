"""
Smart Agro - Flask Backend
Run: python app.py
Requires: pip install flask flask-cors
"""

from flask import Flask, request, jsonify, Response, render_template_string
from flask_cors import CORS
import json
import time
import threading
from datetime import datetime
from collections import deque

app = Flask(__name__)
CORS(app)

# ─── In-memory store ────────────────────────────────────────────────────────
latest_data = {
    "moisture":    0,
    "ph":          7.0,
    "turbidity":   0,
    "turb_status": "CLEAR",
    "timestamp":   None,
    "connected":   False
}

# Keep last 50 readings for history chart
history = deque(maxlen=50)

# SSE clients
sse_clients = []
sse_lock = threading.Lock()

# ─── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the dashboard HTML."""
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.route("/api/sensor-data", methods=["POST"])
def receive_data():
    """ESP32 posts data here every 2 seconds."""
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "No JSON body"}), 400

        now = datetime.now().isoformat()
        latest_data.update({
            "moisture":    round(float(data.get("moisture", 0)), 1),
            "ph":          round(float(data.get("ph", 7.0)), 2),
            "turbidity":   round(float(data.get("turbidity", 0)), 1),
            "turb_status": str(data.get("turb_status", "CLEAR")),
            "timestamp":   now,
            "connected":   True
        })

        # Append to history
        history.append({
            "t":          now,
            "moisture":   latest_data["moisture"],
            "ph":         latest_data["ph"],
            "turbidity":  latest_data["turbidity"],
        })

        # Push to all SSE clients
        _broadcast(latest_data)

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/latest")
def get_latest():
    """Polling fallback — returns the most recent reading."""
    return jsonify(latest_data)


@app.route("/api/history")
def get_history():
    """Returns the last 50 readings."""
    return jsonify(list(history))


@app.route("/api/stream")
def stream():
    """Server-Sent Events endpoint for real-time push."""
    def event_generator():
        q = []
        with sse_lock:
            sse_clients.append(q)
        try:
            # Send current data immediately on connect
            yield _format_sse(latest_data)
            while True:
                if q:
                    msg = q.pop(0)
                    yield _format_sse(msg)
                else:
                    # Heartbeat every 5 s to keep connection alive
                    yield ": heartbeat\n\n"
                time.sleep(1)
        except GeneratorExit:
            with sse_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        }
    )


# ─── Helpers ────────────────────────────────────────────────────────────────

def _format_sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


def _broadcast(data: dict):
    with sse_lock:
        for q in sse_clients:
            q.append(dict(data))


# ─── Disconnect watchdog ─────────────────────────────────────────────────────
def watchdog():
    """Mark device offline if no data received for 10 seconds."""
    while True:
        time.sleep(5)
        if latest_data["timestamp"]:
            last = datetime.fromisoformat(latest_data["timestamp"])
            if (datetime.now() - last).seconds > 10:
                if latest_data["connected"]:
                    latest_data["connected"] = False
                    _broadcast(latest_data)


threading.Thread(target=watchdog, daemon=True).start()


# ─── Entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Smart Agro Flask Server ===")
    print("Dashboard : http://0.0.0.0:5000")
    print("API       : http://0.0.0.0:5000/api/latest")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)