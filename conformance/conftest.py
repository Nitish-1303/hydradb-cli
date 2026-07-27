"""Shared fixtures for the conformance runner.

The runner drives ``vectors.json`` through the real wrapper against a **mocked
SDK transport** (an ``httpx.MockTransport``). Because the genuine SDK request-
building code runs, we can assert the exact HTTP call the wrapper produces: the
endpoint, the content type, and the body/query fields — the true anti-drift gate
described in CONTRACT §4.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from hydra_db import HydraDB as _SdkHydraDB

from hydradb_cli.hydra import HydraDB

VECTORS_PATH = Path(__file__).parent / "vectors.json"


def load_vectors() -> dict:
    return json.loads(VECTORS_PATH.read_text())


class Recorder:
    """Captures the most recent request the wrapper issued through the SDK."""

    def __init__(self) -> None:
        self.method: str = ""
        self.path: str = ""
        self.content_type: str = ""
        self.params: dict[str, str] = {}
        self.body: bytes = b""

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.method = request.method
        self.path = request.url.path
        self.content_type = request.headers.get("content-type", "")
        self.params = dict(request.url.params)
        self.body = request.content
        # A minimal, universally-parseable envelope so SDK response parsing succeeds.
        return httpx.Response(200, json={"success": True, "data": {}, "meta": {}})

    # -- extraction helpers ---------------------------------------------------

    def json_body(self) -> dict:
        if not self.body:
            return {}
        try:
            return json.loads(self.body)
        except json.JSONDecodeError:
            return {}

    def multipart_fields(self) -> dict[str, Any]:
        """Return {name: value} for the multipart body (text field values decoded)."""
        if "boundary=" not in self.content_type:
            return {}
        boundary = self.content_type.split("boundary=", 1)[1].encode()
        fields: dict[str, Any] = {}
        for part in self.body.split(b"--" + boundary):
            if b'name="' not in part or b"\r\n\r\n" not in part:
                continue
            name = part.split(b'name="', 1)[1].split(b'"', 1)[0].decode()
            value = part.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n", 1)[0]
            if b'filename="' in part.split(b"\r\n\r\n", 1)[0]:
                fields[name] = value  # file part: keep raw bytes
            else:
                fields[name] = value.decode()
        return fields

    def fields(self) -> dict[str, Any]:
        """Unified view of the request payload regardless of encoding."""
        if self.content_type.startswith("multipart/form-data"):
            return self.multipart_fields()
        if self.content_type.startswith("application/json"):
            return self.json_body()
        return dict(self.params)


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


@pytest.fixture
def scope_defaults() -> dict:
    return load_vectors().get("scope_defaults", {})


@pytest.fixture
def wrapper(recorder: Recorder, scope_defaults: dict) -> HydraDB:
    """A wrapper whose SDK talks to the recording mock transport, scoped to the
    vectors' default database/collection."""
    w = HydraDB(
        token="test-token",
        base_url="http://conformance.test",
        database=scope_defaults.get("database"),
        collection=scope_defaults.get("collection"),
    )
    w._sdk = _SdkHydraDB(
        token="test-token",
        base_url="http://conformance.test",
        httpx_client=httpx.Client(transport=httpx.MockTransport(recorder.handler)),
    )
    return w
