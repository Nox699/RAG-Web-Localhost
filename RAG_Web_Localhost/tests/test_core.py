from pathlib import Path
import tempfile

import pytest

from app.core import chunk_text, cosine, safe_filename, DocumentError


def test_chunk_overlap_and_final_window():
    assert chunk_text("a b c d e f g h i j", 6, 2) == ["a b c d e f", "e f g h i j"]
    assert chunk_text("   ") == []


def test_invalid_chunk_settings():
    for size, overlap in [(0, 0), (2, 2), (2, -1), (2.5, 1), (True, 0)]:
        with pytest.raises(ValueError):
            chunk_text("abc", size, overlap)


def test_cosine_geometry():
    assert cosine([1, 0], [2, 0]) == pytest.approx(1)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0)
    assert cosine([1, 0], [-1, 0]) == pytest.approx(-1)


def test_safe_filename_strips_paths_and_rejects_empty():
    assert safe_filename("../../notes.txt") == "notes.txt"
    assert safe_filename("mine noter.txt") == "mine noter.txt"
    with pytest.raises(DocumentError):
        safe_filename("../")
