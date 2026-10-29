#!/usr/bin/env python3
"""Token-protected command endpoint on a GPU box: the agent's replacement for SSH (2026-10-20).

The Claude cloud session cannot open SSH (its egress proxy passes only TLS), but HTTPS works. tunnel.sh runs this on
127.0.0.1 behind a Cloudflare quick tunnel and puts the URL and token in the private HF store; `ops/vast.sh exec`
reads them there. Every request must carry the token. Stdlib only.
  POST /exec   header X-Token, body = bash command, optional header X-Timeout (s, default 120)
               -> combined stdout/stderr, then a last line "[exit N]"
  GET  /health -> "ok" (no token; for checking that the tunnel is up)
"""
import hmac, http.server, os, subprocess, sys

TOKEN = open(os.environ.get("REXEC_TOKEN_FILE", "/root/.rexec_token")).read().strip()
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class H(http.server.BaseHTTPRequestHandler):
    def _send(self, code, text):
        b = text.encode(errors="replace")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send(200, "ok\n") if self.path == "/health" else self._send(404, "not found\n")

    def do_POST(self):
        if self.path != "/exec":
            return self._send(404, "not found\n")
        if not hmac.compare_digest(self.headers.get("X-Token", ""), TOKEN):
            return self._send(403, "forbidden\n")
        cmd = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        timeout = float(self.headers.get("X-Timeout", 120))
        try:
            p = subprocess.run(["bash", "-c", ". /etc/v2d_env 2>/dev/null; cd /content; " + cmd],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
            out, rc = p.stdout.decode(errors="replace"), p.returncode
        except subprocess.TimeoutExpired as e:
            out, rc = (e.stdout or b"").decode(errors="replace") + f"\n[timeout after {timeout:.0f} s]", 124
        self._send(200, out + f"\n[exit {rc}]\n")

    def log_message(self, fmt, *args):  # keep the command log (no bodies, no tokens)
        sys.stderr.write("rexec %s %s\n" % (self.address_string(), fmt % args))


http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
