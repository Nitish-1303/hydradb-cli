"""Unit tests for the hand-owned SDK wrapper (``hydradb_cli.hydra``).

The wrapper is exercised against the real SDK wired to an ``httpx.MockTransport``
so genuine request-building and response-parsing run, plus a few direct unit
tests for envelope unwrapping and error translation.
"""

import json

import httpx
import pytest
from hydra_db import HydraDB as _SdkHydraDB
from hydra_db.core.api_error import ApiError
from hydra_db.errors.bad_request_error import BadRequestError
from hydra_db.errors.not_found_error import NotFoundError
from hydra_db.types.handler_error_response import HandlerErrorResponse

from hydradb_cli.hydra import HydraDB, HydraDBClientError
from hydradb_cli.hydra.client import _bool_str, _is_envelope, _unwrap


class _FakeEnvelope:
    def __init__(self, data):
        self.data = data
        self.success = True
        self.meta = None


def _wrapper_with_response(response_json, status=200, captured=None):
    """Build a wrapper whose SDK returns ``response_json`` for any request."""

    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured["request"] = request
        return httpx.Response(status, json=response_json)

    w = HydraDB(token="x", base_url="http://test.local", database="db_test", collection="col_test")
    w._sdk = _SdkHydraDB(
        token="x", base_url="http://test.local", httpx_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    return w


class TestUnwrap:
    def test_is_envelope_true(self):
        assert _is_envelope(_FakeEnvelope({"a": 1}))

    def test_is_envelope_false_for_plain_dict_model(self):
        class Bare:
            chunks = []

        assert not _is_envelope(Bare())

    def test_unwrap_returns_data(self):
        assert _unwrap(_FakeEnvelope({"chunks": [1]})) == {"chunks": [1]}

    def test_unwrap_null_data_is_empty_dict(self):
        assert _unwrap(_FakeEnvelope(None)) == {}

    def test_bool_str(self):
        assert _bool_str(True) == "true"
        assert _bool_str(False) == "false"
        assert _bool_str(None) is None


class TestQuery:
    def test_query_unwraps_and_scopes(self):
        captured = {}
        env = {"success": True, "data": {"chunks": [{"chunk_content": "hi", "relevancy_score": 0.9}]}, "meta": {}}
        w = _wrapper_with_response(env, captured=captured)
        result = w.context.query(query="q", kind="memory")
        assert result["chunks"][0]["chunk_content"] == "hi"
        body = json.loads(captured["request"].content)
        assert body["type"] == "memory"
        assert body["database"] == "db_test"
        assert body["collection"] == "col_test"


class TestIngest:
    def test_ingest_memory_encodes_memories(self):
        captured = {}
        w = _wrapper_with_response({"success": True, "data": {"success_count": 1}, "meta": {}}, captured=captured)
        w.context.ingest(kind="memory", text="dark mode", title="pref")
        request = captured["request"]
        assert request.headers["content-type"].startswith("multipart/form-data")
        assert b'name="memories"' in request.content
        assert b"dark mode" in request.content
        assert b'name="app_knowledge"' not in request.content

    def test_ingest_knowledge_text_becomes_document(self):
        captured = {}
        w = _wrapper_with_response({"success": True, "data": {}, "meta": {}}, captured=captured)
        w.context.ingest(kind="knowledge", text="report", title="Q3")
        request = captured["request"]
        assert request.headers["content-type"].startswith("multipart/form-data")
        assert b'name="documents"' in request.content
        assert b'name="type"' in request.content
        assert b"knowledge" in request.content
        assert b'name="app_knowledge"' not in request.content

    def test_ingest_many_merges_results(self):
        # Each file gets one call; results and counts are merged.
        w = _wrapper_with_response(
            {"success": True, "data": {"success_count": 1, "failed_count": 0, "results": [{"id": "x"}]}, "meta": {}}
        )
        docs = [("a.txt", b"aaa", None), ("b.txt", b"bbb", None)]
        result = w.context.ingest_many(kind="knowledge", documents=docs)
        assert result["success_count"] == 2
        assert len(result["results"]) == 2


class TestListFlatten:
    def test_list_flattens_inner(self):
        env = {"success": True, "data": {"inner": {"sources": [{"id": "s1"}], "total": 1}}, "meta": {}}
        w = _wrapper_with_response(env)
        result = w.context.list(kind="knowledge")
        assert result["sources"][0]["id"] == "s1"
        assert result["total"] == 1
        assert "inner" not in result


class TestScope:
    def test_missing_database_raises(self):
        w = HydraDB(token="x", base_url="http://test.local")  # no default database
        with pytest.raises(HydraDBClientError) as exc:
            w.context.query(query="q")
        assert exc.value.status_code == 0
        assert "database" in exc.value.detail.lower()


class TestErrorTranslation:
    def test_bad_request_becomes_client_error(self):
        body = {"success": False, "error": {"code": "BAD", "message": "bad input"}}
        w = _wrapper_with_response(body, status=400)
        with pytest.raises(HydraDBClientError) as exc:
            w.databases.create(database="x")
        assert exc.value.status_code == 400
        assert "bad input" in exc.value.detail

    def test_not_found_becomes_client_error(self):
        w = _wrapper_with_response({"detail": "nope"}, status=404)
        with pytest.raises(HydraDBClientError) as exc:
            w.context.inspect(id="missing")
        assert exc.value.status_code == 404

    def test_network_error_is_status_zero(self):
        def handler(request):
            raise httpx.ConnectError("refused")

        w = HydraDB(token="x", base_url="http://test.local", database="db_test")
        w._sdk = _SdkHydraDB(
            token="x", base_url="http://test.local", httpx_client=httpx.Client(transport=httpx.MockTransport(handler))
        )
        with pytest.raises(HydraDBClientError) as exc:
            w.databases.list()
        assert exc.value.status_code == 0

    def test_translate_from_sdk_exception_types(self):
        from hydradb_cli.hydra import translate_sdk_error

        err = BadRequestError(body=HandlerErrorResponse(success=False))
        assert isinstance(translate_sdk_error(err), HydraDBClientError)
        assert translate_sdk_error(err).status_code == 400
        assert translate_sdk_error(NotFoundError(body={"x": 1})).status_code == 404
        assert translate_sdk_error(ApiError(status_code=503, body="down")).status_code == 503
