from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from tmt_quantum_vault import ollama_api


def _response_mock(
    *,
    payload: object,
    text: str = "",
    status_code: int = 200,
) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.text = text
    response.status_code = status_code
    response.raise_for_status.return_value = None
    return response


@pytest.mark.parametrize(
    ("system", "expected_system"),
    [
        ("", False),
        ("You are helpful", True),
    ],
)
def test_run_posts_expected_payload(system: str, expected_system: bool) -> None:
    response = _response_mock(
        payload={
            "response": "  completed  ",
            "done": True,
            "total_duration": 42,
        }
    )

    with patch.object(ollama_api.requests, "post", return_value=response) as mock_post:
        result = ollama_api.run(
            model="qwen3:8b",
            prompt="Hello",
            system=system,
            headers={"Authorization": "Bearer token"},
        )

    assert result.model == "qwen3:8b"
    assert result.response == "completed"
    assert result.done is True
    assert result.total_duration_ns == 42
    called_json = mock_post.call_args.kwargs["json"]
    assert ("system" in called_json) is expected_system
    assert called_json["options"]["num_predict"] == 512
    assert called_json["options"]["temperature"] == 0.7


def test_list_models_returns_names() -> None:
    response = _response_mock(
        payload={"models": [{"name": "qwen3:8b"}, {"name": "phi4:latest"}]}
    )

    with patch.object(ollama_api.requests, "get", return_value=response):
        models = ollama_api.list_models()

    assert models == ["qwen3:8b", "phi4:latest"]


def test_extract_error_message_prefers_json_error_and_falls_back_to_text() -> None:
    response = _response_mock(
        payload={"error": "  request failed  "},
        text="plain fallback",
        status_code=400,
    )
    assert ollama_api.extract_error_message(response) == "request failed"

    response.json.side_effect = ValueError("not json")
    response.text = "  plain fallback  "
    assert ollama_api.extract_error_message(response) == "plain fallback"

    response.text = "   "
    assert ollama_api.extract_error_message(response) == "HTTP 400"


def test_run_returns_failure_response_on_http_error() -> None:
    error_response = _response_mock(
        payload={"error": "model not found"},
        text="model not found",
        status_code=404,
    )
    error_response.raise_for_status.side_effect = requests.HTTPError(
        "404 Client Error", response=error_response
    )

    with patch.object(ollama_api.requests, "post", return_value=error_response):
        result = ollama_api.run(model="qwen3:8b", prompt="Hello")

    assert result.returncode == 404
    assert "not found" in result.response
    assert result.done is False


def test_run_returns_failure_response_on_connection_error() -> None:
    with patch.object(
        ollama_api.requests,
        "post",
        side_effect=requests.ConnectionError("Connection refused"),
    ):
        result = ollama_api.run(model="qwen3:8b", prompt="Hello")

    assert result.returncode == 1
    assert "Connection refused" in result.response
    assert result.done is False


def test_is_available_returns_true_and_false_based_on_request_result() -> None:
    with patch.object(ollama_api.requests, "get", return_value=MagicMock()):
        assert ollama_api.is_available() is True

    with patch.object(
        ollama_api.requests,
        "get",
        side_effect=requests.RequestException("offline"),
    ):
        assert ollama_api.is_available() is False
