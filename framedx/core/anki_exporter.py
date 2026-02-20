import hashlib
import os
import random
from pathlib import Path

import genanki

from framedx.core.matcher import CardPair

# Stable model ID derived from project name
_MODEL_ID = 1607392319

_MODEL = genanki.Model(
    _MODEL_ID,
    "FrameDX - Medical Flashcard",
    fields=[
        {"name": "Image"},
        {"name": "Description"},
        {"name": "Source"},
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": "{{Image}}",
            "afmt": '{{FrontSide}}<hr id="answer">{{Description}}<br><small>{{Source}}</small>',
        },
    ],
    css=(
        ".card { font-family: arial; font-size: 20px; text-align: center; "
        "color: black; background-color: white; }\n"
        "img { max-width: 100%; max-height: 80vh; }"
    ),
)


def _stable_id(text: str) -> int:
    """Generate a stable integer ID from a string."""
    h = hashlib.md5(text.encode()).hexdigest()
    return int(h[:8], 16)


def export_deck(
    pairs: list[CardPair],
    deck_name: str,
    output_path: str,
    source_tag: str = "",
) -> str:
    """Export card pairs as an Anki .apkg file.

    Returns the path to the created .apkg file.
    """
    deck_id = _stable_id(deck_name)
    deck = genanki.Deck(deck_id, deck_name)

    media_files = []

    for pair in pairs:
        if not pair.included:
            continue

        img_path = Path(pair.image_path)
        img_filename = img_path.name
        media_files.append(str(img_path))

        note = genanki.Note(
            model=_MODEL,
            fields=[
                f'<img src="{img_filename}">',
                pair.transcript_text,
                source_tag,
            ],
            tags=[source_tag.replace(" ", "_")] if source_tag else [],
        )
        deck.add_note(note)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    package = genanki.Package(deck)
    package.media_files = media_files
    package.write_to_file(str(output_file))

    return str(output_file)
