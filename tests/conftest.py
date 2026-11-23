import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pytest  # noqa: E402


@pytest.fixture
def sample_words():
    import json

    with open(ROOT / "tests" / "sample-words.json", encoding="utf-8") as f:
        return json.load(f)["words"]


@pytest.fixture
def video_1080():
    return {"width": 1080, "height": 1920, "fps": 30.0, "durationMs": 32000}
