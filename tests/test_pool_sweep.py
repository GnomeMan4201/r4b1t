import sqlite3
import threading
import unittest

import requests

import pool_sweep


class FakeResponse:
    def __init__(self, status_code, url):
        self.status_code = status_code
        self.url = url
        self.closed = False

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, head_status=200, get_status=200, final_url=None):
        self.head_status = head_status
        self.get_status = get_status
        self.final_url = final_url
        self.head_calls = 0
        self.get_calls = 0

    def head(self, url, **kwargs):
        self.head_calls += 1
        return FakeResponse(self.head_status, self.final_url or url)

    def get(self, url, **kwargs):
        self.get_calls += 1
        return FakeResponse(self.get_status, self.final_url or url)


class RaisingSession:
    def head(self, url, **kwargs):
        raise requests.exceptions.Timeout("synthetic timeout")


class PoolSweepTests(unittest.TestCase):
    def setUp(self):
        self.limiter = pool_sweep.RateLimiter(min_gap=0)

    def test_registered_domain_removes_only_literal_www_prefix(self):
        self.assertEqual(
            pool_sweep.registered_domain("https://www.example.com/a"),
            "example.com",
        )
        self.assertEqual(
            pool_sweep.registered_domain("https://walmart.example/a"),
            "walmart.example",
        )
        self.assertEqual(
            pool_sweep.registered_domain("https://m.example/a"),
            "m.example",
        )

    def test_status_classification_is_conservative(self):
        self.assertEqual(pool_sweep.classify_status(200), 1)
        self.assertEqual(pool_sweep.classify_status(302), 1)
        self.assertEqual(pool_sweep.classify_status(404), 0)
        self.assertEqual(pool_sweep.classify_status(410), 0)
        for status in (401, 403, 429, 500, 503, None):
            self.assertIsNone(pool_sweep.classify_status(status))

    def test_head_rejection_gets_one_bounded_get_fallback(self):
        session = FakeSession(head_status=405, get_status=200)
        status, reachable, redirect = pool_sweep.check_url(
            "https://example.com/resource", session, self.limiter, timeout=1
        )
        self.assertEqual(status, 200)
        self.assertEqual(reachable, 1)
        self.assertIsNone(redirect)
        self.assertEqual(session.head_calls, 1)
        self.assertEqual(session.get_calls, 1)

    def test_confirmed_404_does_not_trigger_get_fallback(self):
        session = FakeSession(head_status=404, get_status=200)
        status, reachable, _ = pool_sweep.check_url(
            "https://example.com/missing", session, self.limiter, timeout=1
        )
        self.assertEqual(status, 404)
        self.assertEqual(reachable, 0)
        self.assertEqual(session.head_calls, 1)
        self.assertEqual(session.get_calls, 0)

    def test_timeout_is_indeterminate_not_missing(self):
        status, reachable, redirect = pool_sweep.check_url(
            "https://example.com/slow", RaisingSession(), self.limiter, timeout=1
        )
        self.assertIsNone(status)
        self.assertIsNone(reachable)
        self.assertIsNone(redirect)

    def test_pending_uses_last_checked_not_status_nullness(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(pool_sweep.SCHEMA)
        urls = ["https://a.example", "https://b.example"]
        pool_sweep.db_init_urls(conn, urls)
        conn.execute(
            "UPDATE pool SET last_checked = 123, status_code = NULL, reachable = NULL "
            "WHERE url = ?",
            (urls[0],),
        )
        conn.commit()
        self.assertEqual(pool_sweep.db_get_pending(conn, urls), [urls[1]])
        conn.close()

    def test_worker_sessions_are_thread_local(self):
        original_session_factory = pool_sweep.requests.Session
        original_state = pool_sweep._thread_state
        created = []
        lock = threading.Lock()
        barrier = threading.Barrier(2)

        class DummySession:
            max_redirects = 0

        def factory():
            instance = DummySession()
            with lock:
                created.append(instance)
            return instance

        pool_sweep.requests.Session = factory
        pool_sweep._thread_state = threading.local()
        ids = []

        def worker():
            first = pool_sweep.get_worker_session()
            barrier.wait()
            second = pool_sweep.get_worker_session()
            self.assertIs(first, second)
            with lock:
                ids.append(id(first))

        try:
            threads = [threading.Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(len(created), 2)
            self.assertEqual(len(set(ids)), 2)
        finally:
            pool_sweep.requests.Session = original_session_factory
            pool_sweep._thread_state = original_state


if __name__ == "__main__":
    unittest.main()
