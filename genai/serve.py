"""ブラウザUI付きローカルサーバー（標準ライブラリのみ・127.0.0.1限定）

使い方:
    python3 serve.py
    → ブラウザで http://127.0.0.1:8765 を開く

外部には一切バインドしない。UIも1ファイル（ui.html）で、外部CDN等の
読み込みはゼロ。機内モードでもそのまま動く。
"""
import json
import pathlib
from http.server import BaseHTTPRequestHandler, HTTPServer

import ask

BASE_DIR = pathlib.Path(__file__).parent
UI_FILE = BASE_DIR / "ui.html"
HOST, PORT = "127.0.0.1", 8765


class Handler(BaseHTTPRequestHandler):

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(200, UI_FILE.read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        if self.path != "/api/ask":
            self._send(404, b"not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            question = str(payload.get("question", "")).strip()
            if not question:
                raise ValueError("質問が空です")
            result = ask.answer(question)
            result.pop("context", None)
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        except Exception as e:
            body = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
            self._send(500, body, "application/json; charset=utf-8")

    def log_message(self, fmt, *args):  # 標準のアクセスログを簡素化
        print(f"  {self.address_string()} {fmt % args}")


def main() -> None:
    server = HTTPServer((HOST, PORT), Handler)
    print(f"起動しました: http://{HOST}:{PORT}  (終了は Ctrl+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止しました。")


if __name__ == "__main__":
    main()
