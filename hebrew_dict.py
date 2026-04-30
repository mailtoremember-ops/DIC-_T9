"""
hebrew_dict.py
מודול ניהול מילון עברי עבור מפענח T9
Hebrew dictionary management for the T9 decoder.
Source: LibreOffice/Mozilla dictionaries (based on Hspell by Nadav Har'El)
"""

import os
import sys
import threading
import urllib.request
from pathlib import Path

# ─── Source ───────────────────────────────────────────────────────────────────
DICT_URL = (
    "https://raw.githubusercontent.com/LibreOffice/dictionaries/"
    "master/he_IL/he_IL.dic"
)
DICT_FILENAME = "he_IL.dic"

# ─── Hebrew Unicode ranges ─────────────────────────────────────────────────────
HEB_START, HEB_END = 0x05D0, 0x05EA   # א–ת (includes final forms)
NIQ_START, NIQ_END = 0x05B0, 0x05C7   # niqqud / cantillation marks

# ─── Module state ─────────────────────────────────────────────────────────────
_word_set: set | None = None
_word_count: int = 0
_lock = threading.Lock()


# ─── Path resolution ───────────────────────────────────────────────────────────

def _bundled_path() -> Path | None:
    """Return path to dictionary bundled inside a PyInstaller EXE, or None."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        p = Path(sys._MEIPASS) / DICT_FILENAME
        if p.exists():
            return p
    return None


def _cache_path() -> Path:
    """Return the user-local cache path for the dictionary."""
    base = os.environ.get("APPDATA") or str(Path.home())
    cache = Path(base) / "T9Hebrew"
    cache.mkdir(parents=True, exist_ok=True)
    return cache / DICT_FILENAME


def dict_path() -> Path:
    """Return the best available dictionary path (bundled → cache)."""
    return _bundled_path() or _cache_path()


# ─── Parsing helpers ──────────────────────────────────────────────────────────

def _strip_niqqud(word: str) -> str:
    return "".join(c for c in word if not (NIQ_START <= ord(c) <= NIQ_END))


def _is_pure_hebrew(word: str) -> bool:
    return bool(word) and all(HEB_START <= ord(c) <= HEB_END for c in word)


# ─── Download ─────────────────────────────────────────────────────────────────

def _download(path: Path, progress_cb=None) -> None:
    if progress_cb:
        progress_cb("מוריד מילון עברי...")

    # opener with a standard User-Agent (some CDN endpoints require it)
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "T9Hebrew/1.0 (Python urllib)")]

    bytes_so_far = 0

    with opener.open(DICT_URL, timeout=60) as src:
        total = int(src.headers.get("Content-Length", 0) or 0)
        with open(path, "wb") as dst:
            while True:
                chunk = src.read(32_768)
                if not chunk:
                    break
                dst.write(chunk)
                bytes_so_far += len(chunk)
                if progress_cb and total > 0:
                    pct = min(100, bytes_so_far * 100 // total)
                    progress_cb(f"מוריד מילון... {pct}%")


# ─── Public API ───────────────────────────────────────────────────────────────

def load_dictionary(progress_cb=None, done_cb=None) -> None:
    """
    Download (if needed) and parse the Hebrew .dic file.
    Thread-safe; safe to call multiple times.
    """
    global _word_set, _word_count

    path = dict_path()
    try:
        if not path.exists():
            _download(path, progress_cb)

        if progress_cb:
            progress_cb("מעבד מילון...")

        words: set[str] = set()
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            next(fh, None)  # skip Hunspell word-count header
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                # base form only (strip Hunspell flag codes after '/')
                word = _strip_niqqud(line.split("/")[0].strip())
                if _is_pure_hebrew(word):
                    words.add(word)

        with _lock:
            _word_set = words
            _word_count = len(words)

        if done_cb:
            done_cb(True, f"מילון נטען: {_word_count:,} מילים")

    except Exception as exc:
        if done_cb:
            done_cb(False, f"שגיאה בטעינת מילון: {exc}")
        raise


def load_dictionary_async(progress_cb=None, done_cb=None) -> threading.Thread:
    """Start dictionary loading in a background daemon thread."""
    t = threading.Thread(
        target=load_dictionary,
        kwargs={"progress_cb": progress_cb, "done_cb": done_cb},
        daemon=True,
    )
    t.start()
    return t


def is_word(word: str) -> bool:
    """Return True if *word* exists in the loaded dictionary."""
    with _lock:
        return _word_set is not None and word in _word_set


def is_loaded() -> bool:
    """Return True when the dictionary has been successfully loaded."""
    with _lock:
        return _word_set is not None


def word_count() -> int:
    """Return the number of loaded words (0 if not yet loaded)."""
    with _lock:
        return _word_count
