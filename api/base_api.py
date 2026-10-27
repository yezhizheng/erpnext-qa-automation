"""Small session-based client for Frappe REST endpoints."""

from __future__ import annotations

from typing import Any

import requests


class BaseAPI:
    def __init__(self, base_url: str, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        return self.session.request(method, url, timeout=self.timeout, **kwargs)

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> requests.Response:
        return self._request("GET", path, params=params)

    def post(self, path: str, *, json: dict[str, Any] | None = None) -> requests.Response:
        return self._request("POST", path, json=json)

    def put(self, path: str, *, json: dict[str, Any] | None = None) -> requests.Response:
        return self._request("PUT", path, json=json)

    def login(self, username: str, password: str) -> requests.Response:
        response = self.post("/api/method/login", json={"usr": username, "pwd": password})
        response.raise_for_status()
        return response

    @staticmethod
    def json_body(response: requests.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:
            raise AssertionError(f"Expected JSON response, got: {response.text[:500]}") from exc
        return body if isinstance(body, dict) else {"data": body}

    @classmethod
    def error_text(cls, response: requests.Response) -> str:
        body = cls.json_body(response)
        return " ".join(
            str(body.get(key, "")) for key in ("exc_type", "exception", "_server_messages", "message", "data")
        ).lower()

