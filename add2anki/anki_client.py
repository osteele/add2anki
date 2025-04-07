"""Client for interacting with the Anki Connect API."""

import json
from typing import Any, cast

import requests
from rich.console import Console

from add2anki.exceptions import AnkiConnectError

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

    def _request(self, action: str, **params: object) -> Any:
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

            if result.get("error"):
                raise AnkiConnectError(f"AnkiConnect error: {result['error']}")

            return result["result"]
        except requests.exceptions.ConnectionError as err:
            raise AnkiConnectError(
                "Could not connect to Anki. Please make sure Anki is running and the AnkiConnect plugin is installed."
            ) from err
        except requests.exceptions.RequestException as e:
            raise AnkiConnectError(f"Request to AnkiConnect failed: {e}") from e
        except (json.JSONDecodeError, KeyError) as e:
            raise AnkiConnectError(f"Invalid response from AnkiConnect: {e}") from e

    def version(self) -> int:
        """Get the version of the AnkiConnect API.

        Returns:
            The version number
        """
        return cast(int, self._request("version"))

    def check_connection(self) -> tuple[bool, str]:
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
        return cast(list[str], self._request("deckNames"))

    def create_deck(self, deck_name: str) -> int:
        """Create a new deck.

        Args:
            deck_name: Name of the deck to create

        Returns:
            Deck ID
        """
        return cast(int, self._request("createDeck", deck=deck_name))

    def add_note(
        self,
        deck_name: str,
        note_type: str,
        fields: dict[str, str],
        audio: dict[str, str | list[str]] | None = None,
        tags: list[str] | None = None,
    ) -> int:
        """Add a note to a deck.

        Args:
            deck_name: Name of the deck to add the note to
            note_type: Type of note to add
            fields: Fields for the note
            audio: Audio data to attach to the note
            tags: List of tags to add to the note

        Returns:
            Note ID
        """
        # Ensure the deck exists
        if deck_name not in self.get_deck_names():
            self.create_deck(deck_name)

        # Prepare the note
        note = {
            "deckName": deck_name,
            "modelName": note_type,
            "fields": fields,
            "options": {"allowDuplicate": False},
            "tags": tags if tags is not None else ["add2anki"],
        }

        # Add audio if provided
        if audio:
            note["audio"] = cast(Any, [audio])

        return cast(int, self._request("addNote", note=note))

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
                        subprocess.run(["ls", anki_path], capture_output=True).returncode == 0
                    )
                elif system == "Windows" or system == "Linux":
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

    def is_background_launch_supported(self) -> bool:
        """Check if background Anki launch is supported on the current platform.

        Returns:
            True if background launch is supported, False otherwise
        """
        import platform

        system = platform.system()
        return system == "Darwin"  # Only macOS is supported currently

    def launch_anki(self, timeout: int = 30) -> tuple[bool, str]:
        """Launch Anki and wait for AnkiConnect to become available.

        Args:
            timeout: Maximum time in seconds to wait for AnkiConnect to become available

        Returns:
            A tuple of (status, message)
        """
        import platform
        import subprocess
        import time

        system = platform.system()
        # Check if background launch is supported on this platform
        if not self.is_background_launch_supported():
            issues_message = (
                "Background launch is not supported on {system}. See docs/issues/background-launch.md for status."
            )
            return False, issues_message.format(system=system)

        try:
            # Only macOS is supported for now
            if system == "Darwin":  # macOS
                subprocess.Popen(["open", "--background", "-a", "Anki"])
            else:
                # This should never happen due to the check above, but just in case
                return False, f"Background launch not implemented for {system}"

            # Wait for AnkiConnect to become available
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    version = self.version()
                    return True, f"Connected to AnkiConnect (version {version})"
                except AnkiConnectError:
                    time.sleep(1)  # Wait 1 second before trying again

            return False, f"Timeout waiting for AnkiConnect to become available after {timeout} seconds"
        except Exception as e:
            return False, f"Error launching Anki: {e}"

    def get_note_types(self) -> list[str]:
        """Get all note types (models) from Anki.

        Returns:
            List of note type names
        """
        return cast(list[str], self._request("modelNames"))

    def get_field_names(self, note_type: str) -> list[str]:
        """Get field names for a specific note type.

        Args:
            note_type: The name of the note type

        Returns:
            List of field names for the note type
        """
        return cast(list[str], self._request("modelFieldNames", modelName=note_type))

    def get_card_templates(self, note_type: str) -> list[str]:
        """Get card templates for a specific note type.

        Args:
            note_type: The name of the note type

        Returns:
            List of card template names for the note type
        """
        templates = cast(dict[str, dict[str, str]], self._request("modelTemplates", modelName=note_type))
        return list(templates.keys())

    def get_model_sort_field(self, note_type: str) -> str | None:
        """Get the field that is used for sorting in the browser.

        Args:
            note_type: The name of the note type

        Returns:
            The name of the sort field, or None if not available
        """
        model_info = cast(dict[str, Any], self._request("modelGetJson", modelName=note_type))
        sort_field_idx = cast(int, model_info.get("sortf", 0))  # Default to first field if not found
        field_names: list[str] = self.get_field_names(note_type)

        # Return the sort field if it exists in the field names
        if field_names and 0 <= sort_field_idx < len(field_names):
            return field_names[sort_field_idx]

        # Otherwise return None
        return None

    def get_first_field(self, note_type: str) -> str | None:
        """Get the first field of a note type, which is usually the required field.

        Args:
            note_type: The name of the note type

        Returns:
            The name of the first field, or None if there are no fields
        """
        field_names = self.get_field_names(note_type)
        return field_names[0] if field_names else None
