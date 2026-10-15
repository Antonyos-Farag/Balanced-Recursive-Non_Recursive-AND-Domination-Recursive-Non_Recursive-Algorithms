"""Tests for ``tools/serve_playground.py``.

    python -m unittest tests.test_serve_playground

The playground is loaded through a proxy in a live preview, so the four things
that proxy cares about -- protocol version, listen backlog, an explicit charset,
and a no-cache rule -- are asserted here rather than trusted.  The server is
started on an ephemeral port (``port=0``) in a background thread, so running the
suite can never collide with a preview that is already serving port 8000.
"""

from __future__ import annotations

import http.client
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from tools.serve_playground import PLAYGROUND, PlaygroundHandler, PlaygroundServer, make_server

__all__ = ["TestTheRunningServer", "TestTheServerConfiguration"]

INDEX = PLAYGROUND / "index.html"


class _ServerThread:
    """A server plus the thread that runs it, closed on the way out."""

    def __init__(self, directory: Path | None = None) -> None:
        # quiet=True: a test run should not print a line per request next to the
        # assertions, and the log line itself is exercised below.
        self.server = make_server(bind="127.0.0.1", port=0, directory=directory, quiet=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def port(self) -> int:
        return self.server.server_address[1]

    def url(self, path: str = "/") -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class TestTheRunningServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serving = _ServerThread()

    @classmethod
    def tearDownClass(cls):
        cls.serving.stop()

    def test_it_serves_the_playground_page_byte_for_byte(self):
        with urlopen(self.serving.url("/"), timeout=5) as response:
            body = response.read()
        self.assertEqual(response.status, 200)
        self.assertEqual(body, INDEX.read_bytes())

    def test_the_content_type_names_its_charset(self):
        # The page is full of box-drawing characters and em dashes; a browser
        # should never have to guess which encoding they are in.
        with urlopen(self.serving.url("/"), timeout=5) as response:
            self.assertEqual(response.headers["Content-Type"], "text/html; charset=utf-8")

    def test_it_forbids_caching(self):
        with urlopen(self.serving.url("/"), timeout=5) as response:
            self.assertEqual(response.headers["Cache-Control"], "no-store, must-revalidate")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_it_speaks_http_11_and_keeps_the_connection_alive(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.serving.port, timeout=5)
        try:
            # Two requests over one socket: the second one is the actual test.
            for _ in range(2):
                connection.request("GET", "/")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(response.version, 11)
                response.read()
        finally:
            connection.close()

    def test_a_missing_file_is_a_404_and_not_a_traceback(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.serving.port, timeout=5)
        try:
            connection.request("GET", "/no-such-page.html")
            response = connection.getresponse()
            self.assertEqual(response.status, 404)
            response.read()
        finally:
            connection.close()

    def test_head_requests_report_the_length_without_a_body(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.serving.port, timeout=5)
        try:
            connection.request("HEAD", "/")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(int(response.headers["Content-Length"]), INDEX.stat().st_size)
            self.assertEqual(response.read(), b"")
        finally:
            connection.close()

    def test_it_stays_inside_the_directory_it_was_given(self):
        # A traversal attempt must not escape: the page next door must be
        # unreachable no matter what the URL says.
        for path in ("/../README.md", "/%2e%2e/README.md", "/..%2fREADME.md"):
            with self.subTest(path=path):
                connection = http.client.HTTPConnection("127.0.0.1", self.serving.port, timeout=5)
                try:
                    connection.request("GET", path)
                    response = connection.getresponse()
                    body = response.read()
                    self.assertIn(response.status, (400, 404))
                    self.assertNotIn(b"Balanced substrings & Dominators", body)
                finally:
                    connection.close()


class TestTheServerConfiguration(unittest.TestCase):
    """The four properties, asserted directly, so they cannot be edited away."""

    def test_it_declares_http_11(self):
        self.assertEqual(PlaygroundHandler.protocol_version, "HTTP/1.1")

    def test_the_listen_queue_is_larger_than_the_stdlib_default(self):
        self.assertGreaterEqual(PlaygroundServer.request_queue_size, 64)

    def test_html_is_utf_8(self):
        self.assertEqual(PlaygroundHandler.extensions_map[".html"], "text/html; charset=utf-8")

    def test_quiet_actually_silences_the_handler(self):
        served = _ServerThread()
        try:
            self.assertTrue(served.server.quiet)
            served.server.quiet = False
            self.assertFalse(served.server.quiet)
        finally:
            served.stop()

    def test_a_missing_directory_is_reported_not_ignored(self):
        with self.assertRaises(SystemExit):
            make_server(bind="127.0.0.1", port=0, directory=Path("/no/such/playground"))

    def test_the_default_directory_is_the_playground_and_it_exists(self):
        self.assertTrue(PLAYGROUND.is_dir())
        self.assertTrue(INDEX.is_file())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
