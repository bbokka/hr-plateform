"""Download the jobzilla skills taxonomy (real open-source dataset) used by cv_parser.

Source: https://github.com/kingabzpro/jobzilla_ai (jz_skill_patterns.jsonl)
The file ships ~2.1k skills as spaCy EntityRuler patterns, so we load it
directly without hand-typing any terms.
"""
from pathlib import Path
import requests

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SAVE_PATH = DATA_DIR / "jz_skill_patterns.jsonl"
SOURCE_URL = (
    "https://raw.githubusercontent.com/kingabzpro/jobzilla_ai/main/"
    "jz_skill_patterns.jsonl"
)


def download_skills(force: bool = False) -> Path:
    if SAVE_PATH.exists() and not force:
        return SAVE_PATH

    DATA_DIR.mkdir(exist_ok=True)
    resp = requests.get(SOURCE_URL, timeout=60)
    resp.raise_for_status()
    SAVE_PATH.write_text(resp.text, encoding="utf-8")
    return SAVE_PATH


if __name__ == "__main__":
    path = download_skills()
    print(f"Skills taxonomy ready: {path}")