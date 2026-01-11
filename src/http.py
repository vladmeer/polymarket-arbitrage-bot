"""
Polymarket Arbitrage Bot - HTTP Session Utilities

Provides thread-local HTTP session management to ensure thread safety
when making HTTP requests. This module prevents cross-thread session
reuse, which can cause connection pooling issues in multi-threaded
environments.

Thread Safety:
    Each thread gets its own requests.Session instance, ensuring that
    connection pools, cookies, and session state are properly isolated.
    This prevents potential race conditions and connection reuse issues
    when making concurrent HTTP requests.

Usage:
    from src.http import ThreadLocalSessionMixin
    import requests

    class MyHTTPClient(ThreadLocalSessionMixin, requests.Session):
        def make_request(self, url):
            # Each thread gets its own session
            response = self.session.get(url)
            return response.json()

Note:
    This mixin should be used with classes that inherit from
    requests.Session or similar HTTP client classes. The session
    property is automatically created per thread on first access.
"""

import threading
from typing import Any

import requests


class ThreadLocalSessionMixin:
    """
    Mixin providing a thread-local requests.Session.

    Each thread gets its own Session instance to keep connections isolated.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._session_local = threading.local()
        super().__init__(*args, **kwargs)

    def _get_session(self) -> requests.Session:
        """Get a thread-local session to avoid cross-thread reuse."""
        session = getattr(self._session_local, "session", None)
        if session is None:
            session = requests.Session()
            self._session_local.session = session
        return session

    @property
    def session(self) -> requests.Session:
        """Expose the thread-local session for internal use."""
        return self._get_session()
