"""Offline tests for viz/datawrapper_export.py DatawrapperExporter.

The exporter is an httpx.Client wrapper; tests inject a fake client via the
module-level httpx.Client attribute so the real exporter logic runs with no
network. Covers __init__/available/_get_client/create_chart/_upload_data/
publish_chart/create_and_publish/close + context-manager protocol.
"""

from __future__ import annotations

from typing import Any

import pytest

from serbian_data_mcp.viz import datawrapper_export as dw_mod
from serbian_data_mcp.viz.datawrapper_export import DatawrapperExporter


class _FakeResp:
    def __init__(self, payload: dict[str, Any] | None = None, raise_exc: Exception | None = None) -> None:
        self._payload = payload or {}
        self._raise = raise_exc

    def raise_for_status(self) -> None:
        if self._raise is not None:
            raise self._raise

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    """Records post/put calls and returns scripted _FakeResp objects."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.init_args = args
        self.init_kwargs = kwargs
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.is_closed = False
        # Queue of responses per call (post/put in call order). Last one reused.
        self._responses: list[_FakeResp] = []
        self._raises: list[Exception | None] = []

    def set_responses(self, responses: list[_FakeResp]) -> _FakeClient:
        self._responses = list(responses)
        return self

    def _next(self) -> _FakeResp:
        if not self._responses:
            return _FakeResp()
        if len(self._responses) == 1:
            return self._responses[0]
        return self._responses.pop(0)

    def post(self, path: str, **kwargs: Any) -> _FakeResp:
        self.calls.append(("post", path, kwargs))
        return self._next()

    def put(self, path: str, **kwargs: Any) -> _FakeResp:
        self.calls.append(("put", path, kwargs))
        return self._next()

    def close(self) -> None:
        self.is_closed = True


def _install_fake_client(monkeypatch: pytest.MonkeyPatch, responses: list[_FakeResp] | None = None) -> _FakeClient:
    fake = _FakeClient()
    if responses is not None:
        fake.set_responses(responses)
    monkeypatch.setattr(dw_mod.httpx, "Client", lambda *a, **kw: fake)
    return fake


# --- __init__ / available -------------------------------------------------


def test_init_token_from_arg() -> None:
    exp = DatawrapperExporter(token="abc")
    assert exp.token == "abc"
    assert exp._client is None


def test_init_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAWRAPPER_ACCESS_TOKEN", "envtok")
    exp = DatawrapperExporter()
    assert exp.token == "envtok"
    assert exp._client is None


def test_init_no_token() -> None:
    exp = DatawrapperExporter(token=None)
    assert exp.token is None
    assert exp.available is False


def test_available_truthy_with_token() -> None:
    assert DatawrapperExporter(token="t").available is True


# --- _get_client ----------------------------------------------------------


def test_get_client_no_token_raises() -> None:
    exp = DatawrapperExporter(token=None)
    with pytest.raises(RuntimeError, match="requires an API token"):
        exp._get_client()


def test_get_client_creates_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def factory(*args: Any, **kwargs: Any) -> _FakeClient:
        client = _FakeClient(*args, **kwargs)
        captured["client"] = client
        return client

    monkeypatch.setattr(dw_mod.httpx, "Client", factory)
    exp = DatawrapperExporter(token="t")

    c1 = exp._get_client()
    c2 = exp._get_client()
    assert c1 is c2  # cached
    assert c1 is captured["client"]
    # httpx.Client configured with base_url + Authorization bearer header
    assert c1.init_kwargs["base_url"] == "https://api.datawrapper.de/v3"
    assert c1.init_kwargs["headers"]["Authorization"] == "Bearer t"
    assert c1.init_kwargs["timeout"] == 30.0


def test_get_client_recreates_when_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    instances: list[_FakeClient] = []
    monkeypatch.setattr(dw_mod.httpx, "Client", lambda *a, **kw: instances.append(_FakeClient(a, kw)) or instances[-1])
    exp = DatawrapperExporter(token="t")

    c1 = exp._get_client()
    c1.is_closed = True  # simulate a closed client
    c2 = exp._get_client()
    assert c1 is not c2
    assert len(instances) == 2


# --- create_chart ---------------------------------------------------------


def test_create_chart_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch, [_FakeResp({"id": "C1", "url": "http://u"})])
    exp = DatawrapperExporter(token="t")

    data = [{"region": "BG", "value": 10}, {"region": "NS", "value": 20}]
    result = exp.create_chart(data, "Title")

    assert result == {"id": "C1", "url": "http://u"}
    # POST /charts then PUT /charts/C1/data (upload). Two calls total.
    assert (client.calls[0][0], client.calls[0][1]) == ("post", "/charts")
    assert client.calls[0][2]["json"]["title"] == "Title"
    assert client.calls[0][2]["json"]["type"] == "d3-bars-vertical"
    # No labels → no "describe" block
    assert "describe" not in client.calls[0][2]["json"]["metadata"]


def test_create_chart_with_labels_adds_describe_block(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch, [_FakeResp({"id": "C2"})])
    exp = DatawrapperExporter(token="t")

    data = [{"region": "BG", "value": 10}]
    exp.create_chart(data, "T", labels={"region": "Okrug", "value": "Vrednost"})

    describe = client.calls[0][2]["json"]["metadata"]["describe"]
    # First column typed text, rest number
    assert describe["region"] == {"name": "Okrug", "type": "text"}
    assert describe["value"] == {"name": "Vrednost", "type": "number"}


def test_create_chart_labels_with_empty_data_yields_no_describe(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch, [_FakeResp({"id": "C3"})])
    exp = DatawrapperExporter(token="t")

    exp.create_chart([], "T", labels={"region": "Okrug"})
    # data empty → col_names == [] → describe dict empty (comprehension over no cols)
    assert client.calls[0][2]["json"]["metadata"]["describe"] == {}


def test_create_chart_with_metadata_merges(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch, [_FakeResp({"id": "C4"})])
    exp = DatawrapperExporter(token="t")

    exp.create_chart([{"x": 1}], "T", metadata={"axes": {"y": "v"}, "visualize": {"basemaps": "custom"}})

    md = client.calls[0][2]["json"]["metadata"]
    assert md["axes"] == {"y": "v"}
    # update merges, so visualize.basemaps overwritten from custom
    assert md["visualize"]["basemaps"] == "custom"


def test_create_chart_raise_for_status_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, [_FakeResp(raise_exc=RuntimeError("401 unauthorized"))])
    exp = DatawrapperExporter(token="t")

    with pytest.raises(RuntimeError, match="401 unauthorized"):
        exp.create_chart([{"x": 1}], "T")


# --- _upload_data ---------------------------------------------------------


def test_upload_data_empty_data_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch)
    exp = DatawrapperExporter(token="t")
    exp._upload_data("C1", [])  # no data → early return, no PUT
    assert all(c[0] != "put" for c in client.calls)


def test_upload_data_builds_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch, [_FakeResp({"ok": True})])
    exp = DatawrapperExporter(token="t")

    data = [{"region": "BG", "value": 10}, {"region": "NS", "value": 20}]
    exp._upload_data("C1", data)

    put_calls = [c for c in client.calls if c[0] == "put"]
    assert len(put_calls) == 1
    assert put_calls[0][1] == "/charts/C1/data"
    kwargs = put_calls[0][2]
    assert kwargs["headers"]["Content-Type"] == "text/csv"
    csv = kwargs["content"].decode("utf-8")
    # Header row + 2 data rows
    assert csv == "region,value\nBG,10\nNS,20"


def test_upload_data_missing_keys_render_as_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch, [_FakeResp({"ok": True})])
    exp = DatawrapperExporter(token="t")

    # Second row missing 'value' → str(row.get('value','')) == ''
    exp._upload_data("C1", [{"a": 1, "value": 5}, {"a": 2}])
    csv = [c for c in client.calls if c[0] == "put"][0][2]["content"].decode("utf-8")
    assert csv == "a,value\n1,5\n2,"


# --- publish_chart --------------------------------------------------------


def test_publish_chart_success(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(
        monkeypatch,
        [
            _FakeResp({"ok": True}),  # introduce
            _FakeResp({"url": "https://datawrapper.de/_/PUB"}),  # publish
        ],
    )
    exp = DatawrapperExporter(token="t")

    result = exp.publish_chart("PUB")

    assert result["id"] == "PUB"
    assert result["url"] == "https://datawrapper.de/_/PUB"
    assert result["embed_url"] == "https://datawrapper.de/_/PUB/embed/"
    assert 'src="https://datawrapper.de/_/PUB/embed/"' in result["embed_code"]
    assert 'title="PUB"' in result["embed_code"]
    # introduce then publish, in order
    assert (client.calls[0][0], client.calls[0][1]) == ("post", "/charts/PUB/data/introduce")
    assert (client.calls[1][0], client.calls[1][1]) == ("post", "/charts/PUB/publish")


def test_publish_chart_url_fallback_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(
        monkeypatch,
        [_FakeResp({}), _FakeResp({})],  # publish_data has no 'url' key
    )
    exp = DatawrapperExporter(token="t")

    result = exp.publish_chart("XYZ")
    # Falls back to constructed URL
    assert result["url"] == "https://datawrapper.de/_/XYZ"


def test_publish_chart_introduce_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, [_FakeResp(raise_exc=RuntimeError("introduce failed"))])
    exp = DatawrapperExporter(token="t")

    with pytest.raises(RuntimeError, match="introduce failed"):
        exp.publish_chart("P1")


# --- create_and_publish ---------------------------------------------------


def test_create_and_publish_no_token_graceful_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    # No httpx fake needed — should short-circuit before _get_client
    _install_fake_client(monkeypatch)
    exp = DatawrapperExporter(token=None)

    result = exp.create_and_publish([{"x": 1}], "T")

    assert result["id"] == ""
    assert "error" in result
    assert "DATAWRAPPER_ACCESS_TOKEN" in result["embed_code"]
    assert "API token" in result["error"]


def test_create_and_publish_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(
        monkeypatch,
        [
            _FakeResp({"id": "C1", "url": "u1"}),  # create_chart POST
            _FakeResp({"ok": True}),  # upload PUT
            _FakeResp({"ok": True}),  # introduce
            _FakeResp({"url": "https://datawrapper.de/_/C1"}),  # publish
        ],
    )
    exp = DatawrapperExporter(token="t")

    result = exp.create_and_publish([{"region": "BG", "value": 1}], "Title", chart_type="d3-lines")

    assert result["id"] == "C1"
    assert result["url"] == "https://datawrapper.de/_/C1"
    assert result["embed_url"].endswith("/C1/embed/")
    # 4 sequential calls
    assert len(client.calls) == 4


# --- close / context manager ----------------------------------------------


def test_close_no_client_is_noop() -> None:
    exp = DatawrapperExporter(token=None)
    exp.close()  # _client is None — no crash


def test_close_closes_open_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch)
    exp = DatawrapperExporter(token="t")
    exp._get_client()  # build client
    assert exp._client is not None

    exp.close()
    assert client.is_closed is True


def test_close_idempotent_when_already_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch)
    exp = DatawrapperExporter(token="t")
    exp._get_client()

    exp.close()
    exp.close()  # second close — client.is_closed True, skip re-close
    assert client.is_closed is True


def test_context_manager_closes_on_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _install_fake_client(monkeypatch)

    with DatawrapperExporter(token="t") as exp:
        assert isinstance(exp, DatawrapperExporter)
        exp._get_client()

    assert client.is_closed is True


def test_context_manager_exit_without_client() -> None:
    # __exit__ must not crash when no client was ever built
    with DatawrapperExporter(token=None):
        pass
