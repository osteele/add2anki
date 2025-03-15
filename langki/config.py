"""Configuration management for langki."""

import json
import os
from pathlib import Path
from typing import Any, Optional, TypedDict

from pydantic import BaseModel

# Define field name synonyms
FIELD_SYNONYMS = {
    "hanzi": ["chinese", "characters", "character", "hanzi"],
    "pinyin": ["pronunciation", "reading", "pinyin"],
    "english": ["translation", "meaning", "english"],
}


class LangkiConfig(BaseModel):
    """Configuration for langki."""

    note_type: Optional[str] = None
    last_used_deck: str = "Smalltalk"


class FieldMappingBase(TypedDict):
    """Base type for field mappings with required fields."""

    hanzi_field: str
    pinyin_field: str
    english_field: str


class FieldMapping(FieldMappingBase, total=False):
    """Extended type for field mappings with optional fields."""

    sound_field: Optional[str]


def get_config_dir() -> Path:
    """Get the configuration directory for langki.

    Returns:
        Path to the configuration directory
    """
    if os.name == "nt":  # Windows
        config_dir = Path(os.environ.get("APPDATA", "")) / "langki"
    else:  # macOS, Linux, etc.
        config_dir = Path.home() / ".config" / "langki"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the path to the configuration file.

    Returns:
        Path to the configuration file
    """
    return get_config_dir() / "config.json"


def load_config() -> LangkiConfig:
    """Load configuration from file.

    Returns:
        LangkiConfig object
    """
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            return LangkiConfig(**config_data)
        except (json.JSONDecodeError, ValueError):
            # If the config file is invalid, return default config
            return LangkiConfig()
    return LangkiConfig()


def save_config(config: LangkiConfig) -> None:
    """Save configuration to file.

    Args:
        config: LangkiConfig object to save
    """
    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(), f, indent=2)


def find_matching_field(field_name: str, field_type: str) -> bool:
    """Check if a field name matches a field type using synonyms.

    Args:
        field_name: The field name to check
        field_type: The field type to match against (hanzi, pinyin, or english)

    Returns:
        True if the field name matches the field type, False otherwise
    """
    if field_type not in FIELD_SYNONYMS:
        return False

    field_name_lower = field_name.lower()
    return any(synonym in field_name_lower for synonym in FIELD_SYNONYMS[field_type])


def find_suitable_note_types(anki_client: Any) -> list[tuple[str, FieldMapping]]:
    """Find note types that have fields for Hanzi, Pinyin, and English.

    Args:
        anki_client: AnkiClient instance

    Returns:
        List of tuples containing (note_type_name, field_mapping)
    """
    suitable_note_types: list[tuple[str, FieldMapping]] = []

    # Get all note types
    note_types = anki_client.get_note_types()

    for note_type in note_types:
        # Get fields for this note type
        fields = anki_client.get_field_names(note_type)

        # Check if this note type has suitable fields
        hanzi_field = None
        pinyin_field = None
        english_field = None
        sound_field = None

        for field in fields:
            if find_matching_field(field, "hanzi") and not hanzi_field:
                hanzi_field = field
            elif find_matching_field(field, "pinyin") and not pinyin_field:
                pinyin_field = field
            elif find_matching_field(field, "english") and not english_field:
                english_field = field
            elif "sound" in field.lower() and not sound_field:
                sound_field = field

        # If we found all required fields, add this note type to the list
        if hanzi_field and pinyin_field and english_field:
            field_mapping: FieldMapping = {
                "hanzi_field": hanzi_field,
                "pinyin_field": pinyin_field,
                "english_field": english_field,
            }
            if sound_field:
                field_mapping["sound_field"] = sound_field

            suitable_note_types.append((note_type, field_mapping))

    return suitable_note_types
