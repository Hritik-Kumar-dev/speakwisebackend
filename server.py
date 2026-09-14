"""Dependency-free HTTP API for the SpeakWell scenario-based MVP."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

SCENARIOS = [
    {"id": "stage", "name": "Stage", "description": "Give a speech on the big stage!", "image": "/stage.png"},
    {"id": "concert", "name": "Concert", "description": "Sing or speak to a huge crowd.", "image": "/concert.png"},
    {"id": "interview", "name": "Interview", "description": "Answer questions like a pro.", "image": "/interview.png"},
    {"id": "classroom", "name": "Classroom", "description": "Share an idea in class.", "image": "/classroom.png"},
]


def score_freeform(transcript: str, duration: float = 0) -> dict:
    words = transcript.strip().split()
    word_count = len(words)
    if word_count == 0:
        return {"overall": 0, "pronunciation": 0, "correctness": 0, "fluency": 0, "transcript": transcript, "feedback": [], "alternative": ""}

    avg_word_length = sum(len(word) for word in words) / max(word_count, 1)
    sentences = [sentence for sentence in transcript.split(".") if sentence.strip()]

    correctness = min(100, 60 + word_count * 3 + int(avg_word_length * 3))
    fluency = 60
    if duration > 0:
        wpm = (word_count / max(duration, 1)) * 60
        fluency = max(40, min(100, 100 - abs(wpm - 120) / 2))
    else:
        fluency = min(100, 60 + word_count * 2)

    pronunciation = min(100, 70 + int(avg_word_length * 2))
    overall = round(pronunciation * 0.35 + correctness * 0.35 + fluency * 0.3)

    feedback = [{"type": "strength", "label": "Great speaking!", "detail": f"You used {word_count} words. Keep it up!"}]
    if sentences:
        feedback.append({"type": "tip", "label": "Sentences", "detail": f"You made {len(sentences)} sentence(s). Try to use full sentences to improve clarity."})
    if duration > 0 and word_count / max(duration, 1) < 1:
        feedback.append({"type": "tip", "label": "Pace", "detail": "Try speaking a little more. Longer answers help practice fluency."})

    return {
        "overall": overall,
        "pronunciation": pronunciation,
        "correctness": correctness,
        "fluency": fluency,
        "transcript": transcript,
        "feedback": feedback,
        "alternative": "",
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: object, status: int = 200, content_type: str = "application/json") -> None:
        body = json.dumps(payload).encode() if content_type == "application/json" else payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/scenarios":
            self._send(SCENARIOS)
        else:
            self._send({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/score":
            self._send({"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            result = score_freeform(str(data.get("transcript", "")), float(data.get("duration", 0) or 0))
            self._send(result)
        except (ValueError, json.JSONDecodeError):
            self._send({"error": "Provide a valid transcript and duration."}, 400)

    def log_message(self, *_args: object) -> None:
        return


if __name__ == "__main__":
    print("SpeakWell running at http://localhost:8000")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
