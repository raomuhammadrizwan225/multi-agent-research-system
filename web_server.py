import json
import mimetypes
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
HOST = os.getenv("RESEARCHMIND_HOST", "127.0.0.1")
PORT = int(os.getenv("RESEARCHMIND_PORT", "8501"))


class ResearchMindHandler(BaseHTTPRequestHandler):
    server_version = "ResearchMind/1.0"

    def log_message(self, format, *args):
        print(f"[ResearchMind] {self.address_string()} - {format % args}")

    def _json_response(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        if length <= 0:
            return {}

        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _serve_file(self, relative_path):
        target = (FRONTEND_DIR / relative_path).resolve()
        frontend_root = FRONTEND_DIR.resolve()

        if frontend_root not in target.parents and target != frontend_root:
            self.send_error(403)
            return

        if not target.exists() or not target.is_file():
            self.send_error(404)
            return

        content = target.read_bytes()
        mime_type, _ = mimetypes.guess_type(str(target))

        self.send_response(200)
        self.send_header(
            "Content-Type",
            f"{mime_type or 'application/octet-stream'}; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            self._serve_file("index.html")
            return

        if path == "/styles.css":
            self._serve_file("styles.css")
            return

        if path == "/app.js":
            self._serve_file("app.js")
            return

        if path == "/api/health":
            self._json_response({"status": "ok"})
            return

        self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path

        try:
            body = self._read_json()

            # Lazy import allows the static UI and health endpoint to start
            # before provider credentials are configured.
            from agents import (
                critic_chain,
                generate_report,
                run_reader_agent,
                run_search_agent,
            )

            if path == "/api/search":
                topic = str(body.get("topic", "")).strip()

                if not topic:
                    self._json_response(
                        {"error": "Research topic is required."},
                        400,
                    )
                    return

                result = run_search_agent(topic)
                self._json_response({"result": result})
                return

            if path == "/api/reader":
                topic = str(body.get("topic", "")).strip()
                search_results = str(body.get("search_results", "")).strip()

                if not topic or not search_results:
                    self._json_response(
                        {"error": "Topic and search results are required."},
                        400,
                    )
                    return

                result = run_reader_agent(topic, search_results)
                self._json_response({"result": result})
                return

            if path == "/api/writer":
                topic = str(body.get("topic", "")).strip()
                search_results = str(body.get("search_results", "")).strip()
                reader_results = str(body.get("reader_results", "")).strip()

                if not topic or not reader_results:
                    self._json_response(
                        {"error": "Topic and reader results are required."},
                        400,
                    )
                    return

                research_material = (
                    f"SEARCH RESULTS:\n{search_results}\n\n"
                    f"READER SUMMARIES:\n{reader_results}"
                )

                result = generate_report(topic, research_material)
                self._json_response({"result": result})
                return

            if path == "/api/critic":
                report = str(body.get("report", "")).strip()

                if not report:
                    self._json_response(
                        {"error": "Report is required."},
                        400,
                    )
                    return

                result = critic_chain.invoke({"report": report})
                self._json_response({"result": result})
                return

            self._json_response({"error": "Unknown API endpoint."}, 404)

        except json.JSONDecodeError:
            self._json_response({"error": "Invalid JSON request."}, 400)
        except Exception as exc:
            print("[ResearchMind ERROR]")
            traceback.print_exc()
            self._json_response({"error": str(exc)}, 500)


def main():
    server = ThreadingHTTPServer((HOST, PORT), ResearchMindHandler)
    print("ResearchMind HTML/CSS/JavaScript UI")
    print(f"Local URL: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop the server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping ResearchMind...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
