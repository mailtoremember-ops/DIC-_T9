"""
t9_decoder.py
לוגיקת פענוח T9 עברי
Hebrew T9 decoding logic.

Key mapping (one keypress per letter - predictive T9):
    2 → ד ה ו       6 → ז ח ט
    3 → א ב ג       7 → ר ש ת
    4 → מ ם נ ן     8 → צ ץ ק
    5 → י כ ך ל     9 → ס ע פ ף
    0 → [space / word separator]

Example: 6725076270255037623 → חתול שחור הלך ברחוב
"""

from itertools import product as iterproduct
from hebrew_dict import is_word, is_loaded

# ─── Key map ──────────────────────────────────────────────────────────────────
KEY_MAP: dict[str, list[str]] = {
    "2": ["ד", "ה", "ו"],
    "3": ["א", "ב", "ג"],
    "4": ["מ", "ם", "נ", "ן"],
    "5": ["י", "כ", "ך", "ל"],
    "6": ["ז", "ח", "ט"],
    "7": ["ר", "ש", "ת"],
    "8": ["צ", "ץ", "ק"],
    "9": ["ס", "ע", "פ", "ף"],
    # '0' is the word separator – not a letter key
}

# ─── Letter classification ────────────────────────────────────────────────────
# Final (sofit) forms should appear only at the END of a word
SOFIT: frozenset[str] = frozenset("םןךףץ")

# ─── Candidate generation ─────────────────────────────────────────────────────

def letter_combinations(segment: str) -> list[str]:
    """
    Return every possible Hebrew-letter string for a digit sequence.
    Returns [] for empty/invalid input.
    """
    if not segment:
        return []
    groups: list[list[str]] = []
    for digit in segment:
        letters = KEY_MAP.get(digit)
        if not letters:              # digit 0 or unrecognised
            return []
        groups.append(letters)
    return ["".join(combo) for combo in iterproduct(*groups)]


def _valid_form(word: str) -> bool:
    """True when sofit letters appear only as the last character."""
    if len(word) <= 1:
        return True
    return not any(c in SOFIT for c in word[:-1])


# ─── Segment decoding ─────────────────────────────────────────────────────────

def decode_segment(segment: str) -> dict:
    """
    Decode a single digit segment (no zeros) to Hebrew word candidates.

    Returns a dict:
      segment          – original digit string
      best             – best word to display (str | None)
      dictionary_matches – words found in dictionary (valid form first)
      all_candidates   – up to 20 raw combinations
      valid_candidates – combinations with correct sofit placement
    """
    all_cands = letter_combinations(segment)
    valid_cands = [w for w in all_cands if _valid_form(w)]

    # Prefer valid-form words in dictionary; fall back to all forms
    dict_hits = [w for w in valid_cands if is_word(w)]
    if not dict_hits:
        dict_hits = [w for w in all_cands if is_word(w)]

    best = (
        dict_hits[0]
        if dict_hits
        else (valid_cands[0] if valid_cands else (all_cands[0] if all_cands else None))
    )

    return {
        "segment": segment,
        "best": best,
        "dictionary_matches": dict_hits,
        "all_candidates": all_cands[:20],
        "valid_candidates": valid_cands[:20],
    }


# ─── Full-string decoding ─────────────────────────────────────────────────────

def decode_full(number_string: str) -> tuple[str, list[dict]]:
    """
    Decode a complete T9 digit string to Hebrew text.

    '0' characters act as word separators.
    Multiple consecutive zeros are treated as a single separator.

    Returns:
        result_text  – best-guess Hebrew sentence
        word_data    – list of dicts from decode_segment(), one per word
    """
    # Strip non-digit characters
    cleaned = "".join(c for c in number_string if c.isdigit())
    if not cleaned:
        return "", []

    # Split on runs of zeros to get word segments
    segments: list[str] = []
    current: list[str] = []
    for ch in cleaned:
        if ch == "0":
            if current:
                segments.append("".join(current))
                current = []
        else:
            current.append(ch)
    if current:
        segments.append("".join(current))

    word_data: list[dict] = []
    result_parts: list[str] = []

    for seg in segments:
        data = decode_segment(seg)
        word_data.append(data)
        result_parts.append(data["best"] if data["best"] else f"[{seg}?]")

    return " ".join(result_parts), word_data
