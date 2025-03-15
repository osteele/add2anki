"""Client for interacting with the Anki Connect API."""

import json
from typing import Any, Tuple

import requests
from rich.console import Console

from langki.exceptions import AnkiConnectError

console = Console()


class AnkiClient:
    """Client for interacting with the Anki Connect API."""

    def __init__(self, host: str = "localhost", port: int = 8765) -> None:
        """Initialize the AnkiClient.

        Args:
            host: The host where Anki is running
            port: The port for AnkiConnect
        """
        self.url = f"http://{host}:{port}"

    def _request(self, action: str, **params: Any) -> Any:
        """Make a request to the AnkiConnect API.

        Args:
            action: The action to perform
            **params: Parameters for the action

        Returns:
            The response from AnkiConnect

        Raises:
            AnkiConnectError: If the request fails or returns an error
        """
        request_data = {"action": action, "version": 6, "params": params}
        try:
            response = requests.post(self.url, json=request_data)
            response.raise_for_status()
            result = response.json()

            if "error" in result and result["error"]:
                raise AnkiConnectError(f"AnkiConnect error: {result['error']}")

            return result["result"]
        except requests.exceptions.ConnectionError:
            raise AnkiConnectError(
                "Could not connect to Anki. Please make sure Anki is running and the AnkiConnect plugin is installed."
            )
        except requests.exceptions.RequestException as e:
            raise AnkiConnectError(f"Request to AnkiConnect failed: {e}")
        except (json.JSONDecodeError, KeyError) as e:
            raise AnkiConnectError(f"Invalid response from AnkiConnect: {e}")

    def version(self) -> int:
        """Get the version of the AnkiConnect API.

        Returns:
            The version number
        """
        return self._request("version")

    def check_connection(self) -> Tuple[bool, str]:
        """Check if we can connect to AnkiConnect.

        Returns:
            A tuple of (status, message)
        """
        try:
            version = self.version()
            return True, f"Connected to AnkiConnect (version {version})"
        except AnkiConnectError as e:
            return False, str(e)

    def get_deck_names(self) -> list[str]:
        """Get all deck names.

        Returns:
            List of deck names
        """
        return self._request("deckNames")

    def create_deck(self, deck_name: str) -> int:
        """Create a new deck.

        Args:
            deck_name: Name of the deck to create

        Returns:
            Deck ID
        """
        return self._request("createDeck", deck=deck_name)

    def add_note(
        self,
        deck_name: str,
        note_type: str,
        fields: dict[str, str],
        audio: dict[str, Any] | None = None,
    ) -> int:
        """Add a note to a deck.

        Args:
            deck_name: Name of the deck to add the note to
            note_type: Type of note to add
            fields: Fields for the note
            audio: Audio data to attach to the note

        Returns:
            Note ID
        """
        # Ensure the deck exists
        if deck_name not in self.get_deck_names():
            self.create_deck(deck_name)

        # Prepare the note
        note: dict[str, Any] = {
            "deckName": deck_name,
            "modelName": note_type,
            "fields": fields,
            "options": {"allowDuplicate": False},
            "tags": ["langki"],
        }

        # Add audio if provided
        if audio:
            note["audio"] = [audio]

        return self._request("addNote", note=note)

    def check_anki_status(self) -> tuple[bool, str]:
        """Check if Anki is running and AnkiConnect is available.

        Returns:
            A tuple of (status, message)
        """
        try:
            version = self.version()
            return True, f"Connected to AnkiConnect (version {version})"
        except AnkiConnectError as e:
            if "Could not connect" in str(e):
                # Try to determine if Anki is installed
                import platform
                import shutil
                import subprocess

                system = platform.system()
                anki_installed = False

                if system == "Darwin":  # macOS
                    anki_path = "/Applications/Anki.app"
                    anki_installed = shutil.which("anki") is not None or (
                        subprocess.run(["ls", anki_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode
                        == 0
                    )
                elif system == "Windows":
                    anki_installed = shutil.which("anki") is not None
                elif system == "Linux":
                    anki_installed = shutil.which("anki") is not None

                if not anki_installed:
                    return False, "Anki does not appear to be installed. Please install Anki first."
                else:
                    return (
                        False,
                        "Anki is installed but not running or AnkiConnect plugin is not installed. "
                        "Please start Anki and make sure the AnkiConnect plugin is installed.",
                    )
            return False, f"Error connecting to AnkiConnect: {e}"

    def get_note_types(self) -> list[str]:
        """Get all note types (models) from Anki.

        Returns:
            List of note type names
        """
        return self._request("modelNames")

    def get_field_names(self, note_type: str) -> list[str]:
        """Get field names for a specific note type.

        Args:
            note_type: The name of the note type

        Returns:
            List of field names for the note type
        """
        return self._request("modelFieldNames", modelName=note_type)

    def get_card_templates(self, note_type: str) -> list[str]:
        """Get card templates for a specific note type.

        Args:
            note_type: The name of the note type

        Returns:
            List of card template names for the note type
        """
        model_info = self._request("modelTemplates", modelName=note_type)
        return list(model_info.keys())
