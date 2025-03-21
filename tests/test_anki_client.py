"""Tests for the anki_client module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from add2anki.anki_client import AnkiClient
from add2anki.exceptions import AnkiConnectError


def test_anki_client_init() -> None:
    """Test AnkiClient initialization."""
    client = AnkiClient()
    assert client.url == "http://localhost:8765"

    client = AnkiClient(host="example.com", port=1234)
    assert client.url == "http://example.com:1234"


def test_request_success() -> None:
    """Test successful request to AnkiConnect."""
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "test_result", "error": None}
        mock_post.return_value = mock_response

        client = AnkiClient()
        # Using a private method in tests is acceptable in this case
        # to test the internal functionality
        result = client._request("test_action", param1="value1")  # pylint: disable=protected-access

        assert result == "test_result"
        mock_post.assert_called_once_with(
            "http://localhost:8765",
            json={"action": "test_action", "version": 6, "params": {"param1": "value1"}},
        )


def test_request_error_response() -> None:
    """Test request with error in response."""
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": None, "error": "test_error"}
        mock_post.return_value = mock_response

        client = AnkiClient()
        with pytest.raises(AnkiConnectError, match="AnkiConnect error: test_error"):
            client._request("test_action")  # pylint: disable=protected-access


def test_request_connection_error() -> None:
    """Test request with connection error."""
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection error")

        client = AnkiClient()
        with pytest.raises(AnkiConnectError):
            client._request("test_action")  # pylint: disable=protected-access


def test_version() -> None:
    """Test version method."""
    with patch.object(AnkiClient, "_request") as mock_request:
        mock_request.return_value = 6

        client = AnkiClient()
        version = client.version()

        assert version == 6
        mock_request.assert_called_once_with("version")


def test_check_connection_success() -> None:
    """Test check_connection when successful."""
    with patch.object(AnkiClient, "version") as mock_version:
        mock_version.return_value = 6

        client = AnkiClient()
        result = client.check_connection()

        assert result == (True, "Connected to AnkiConnect (version 6)")
        mock_version.assert_called_once()


def test_check_connection_failure() -> None:
    """Test check_connection when it fails."""
    with patch.object(AnkiClient, "version") as mock_version:
        mock_version.side_effect = AnkiConnectError("Connection error")

        client = AnkiClient()
        result = client.check_connection()

        assert result == (False, "Connection error")
        mock_version.assert_called_once()
