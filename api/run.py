"""POST /api/run  body {"sample": "supplier-pack-03", "approach": "approach4"}  header X-OpenRouter-Key (not for approach1).

Streams newline-delimited JSON (step events, then one result or error). The key is passed to a child process through its
environment only; it is never logged, stored, put in a URL or written to the response.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {f'supplier-pack-{n:02d}' for n in range(1, 11)}
APPROACHES = {'approach1', 'approach2', 'approach3', 'approach4'}


class handler(BaseHTTPRequestHandler):
    def _start(self, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/x-ndjson; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Accel-Buffering', 'no')
        self.end_headers()

    def _error(self, code, message, status=400):
        self._start(status)
        self.wfile.write((json.dumps({'event': 'error', 'code': code, 'message': message}) + '\n').encode())

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            sample, approach = body.get('sample'), body.get('approach')
        except (ValueError, AttributeError):
            return self._error('bad_request', 'Send JSON with "sample" and "approach".')
        if sample not in SAMPLES or approach not in APPROACHES:
            return self._error('bad_request', 'Choose one of the ten sample PDFs and approach1 to approach4.')
        key = (self.headers.get('X-OpenRouter-Key') or '').strip()
        if approach != 'approach1' and (not key or len(key) > 200 or any(c.isspace() for c in key)):
            return self._error('invalid_key', 'Paste your OpenRouter key to run approaches 2 to 4. Approach 1 needs none.', 401)
        env = {k: v for k, v in os.environ.items() if k != 'OPENROUTER_API_KEY'}
        if approach != 'approach1':
            env['OPENROUTER_API_KEY'] = key
        env.setdefault('OPENROUTER_MODEL', 'qwen/qwen3-14b')
        env.setdefault('OPENROUTER_JUDGE_MODEL', 'anthropic/claude-haiku-5.5')
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen([sys.executable, '-m', 'procurement.stream_run', sample, approach], cwd=str(ROOT),
                                       env=env, stdout=subprocess.PIPE, stderr=errors)
            self._start()
            sent = False
            try:
                for line in process.stdout:
                    sent = True
                    self.wfile.write(line)
                    self.wfile.flush()
            except BrokenPipeError:
                process.kill()
            finally:
                process.wait()
            if not sent and process.returncode:
                # The child died before emitting anything: say so, with a redacted tail of its stderr for the logs.
                errors.seek(0)
                tail = errors.read()[-1500:].decode('utf-8', errors='replace')
                if key:
                    tail = tail.replace(key, '[redacted]')
                print(f'stream_run exited {process.returncode}: {tail}', file=sys.stderr)
                self.wfile.write((json.dumps({'event': 'error', 'code': 'provider_error',
                                              'message': 'The check could not start.'}) + chr(10)).encode())

    def log_message(self, *args):  # never log requests: headers carry the visitor's key
        pass
