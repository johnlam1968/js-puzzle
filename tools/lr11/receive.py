"""A tiny receiver for the assumption ledger page.

Serves the practice app and accepts what the page sends, so a painted board can
land straight in the workspace instead of in some download folder.

    python3 lr11/receive.py [--port 8765] [--root <app dir>] [--out <dir>]

The page's "Send to sandbox" button POSTs JSON to /save.  If the browser
cannot reach the server the page says so and you fall back to copying the
text out of the JSON box.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class Handler(SimpleHTTPRequestHandler):
    out_dir = "/workspace/output/incoming"

    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path.split("?")[0] != "/save":
            return self._json(404, {"ok": False, "error": "unknown path"})
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception as e:
            return self._json(400, {"ok": False, "error": "bad json: %s" % e})
        os.makedirs(self.out_dir, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        written = []
        board = data.get("board") or {}
        p = os.path.join(self.out_dir, "board-%s.json" % stamp)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(board, fh, indent=2)
        written.append(p)
        img = data.get("png")
        if isinstance(img, str) and img.startswith("data:image/png;base64,"):
            import base64
            q = os.path.join(self.out_dir, "board-%s.png" % stamp)
            with open(q, "wb") as fh:
                fh.write(base64.b64decode(img.split(",", 1)[1]))
            written.append(q)
        print("[receive] %s -> %s" % (stamp, ", ".join(written)), flush=True)
        self._json(200, {"ok": True, "written": written})

    def log_message(self, fmt, *args):
        print("[receive] " + fmt % args, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--root", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                                   "pz", "app", "jane-street-puzzle-practice-main"))
    ap.add_argument("--out", default="/workspace/output/incoming")
    args = ap.parse_args()
    Handler.out_dir = args.out
    os.chdir(args.root)
    os.makedirs(args.out, exist_ok=True)
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("serving %s on :%d, writing to %s" % (args.root, args.port, args.out), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
