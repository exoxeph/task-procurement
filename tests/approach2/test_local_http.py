"""Real loopback HTTP checks for proxy bypass and redirect refusal."""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from threading import Thread
import unittest
from unittest.mock import patch
from urllib.request import Request

from procurement.approach2.extractor import _read_http


@contextmanager
def local_server(redirect=False):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get('Content-Length', '0')))
            self.send_response(302 if redirect else 200)
            if redirect:
                self.send_header('Location', 'http://127.0.0.1:1/elsewhere')
            self.end_headers()
            self.wfile.write(b'local response')

        def log_message(self, *args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/api/chat'
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class LocalHttpTests(unittest.TestCase):
    def test_private_post_bypasses_ambient_proxy(self):
        proxy = {'http_proxy': 'http://127.0.0.1:1', 'HTTP_PROXY': 'http://127.0.0.1:1',
                 'NO_PROXY': '', 'no_proxy': ''}
        with local_server() as url, patch.dict(os.environ, proxy, clear=True), patch('urllib.request._opener', None):
            self.assertEqual(_read_http(Request(url, data=b'private quotation'), 2), 'local response')

    def test_redirect_is_refused_before_contacting_another_destination(self):
        with local_server(redirect=True) as url, patch.dict(os.environ, {}, clear=True), patch(
                'urllib.request._opener', None), self.assertRaisesRegex(ValueError, 'redirect'):
            _read_http(Request(url, data=b'private quotation'), 2)
