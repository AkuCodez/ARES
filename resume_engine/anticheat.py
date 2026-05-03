# resume_engine/anticheat.py

import re

# Thresholds
_MIN_SUSPICIOUS_LEN   = 300   # chars — suspiciously long for depth 1
_MAX_FILLER_RATIO     = 0.15  # too many filler words = copy-paste padding
_STRUCTURE_PATTERNS   = [
    r"\d+\.\s",          # numbered lists "1. 2. 3."
    r"firstly|secondly|thirdly|furthermore|moreover|in conclusion",
    r"it is (important|worth|essential) to note",
    r"in summary|to summarize|overall,",
]

_FILLER_WORDS = {
    "basically", "essentially", "generally", "obviously",
    "clearly", "simply", "just", "very", "really", "quite"
}


def detect_cheating(answer: str, depth: int) -> dict:
    """
    Heuristic anti-cheat analysis.

    Flags:
      - too_long:      depth-1 answer suspiciously detailed (likely GPT)
      - ai_structure:  formal essay structure (numbered lists, transitions)
      - filler_heavy:  high ratio of filler/padding words
      - perfect_depth: answer depth far exceeds claimed skill level

    Returns:
        {
            "flagged": bool,
            "flags":   list[str],
            "risk":    "low" | "medium" | "high"
        }
    """
    flags = []
    words = answer.split()
    word_count = len(words)

    # Flag 1: too long for depth level
    if depth == 1 and len(answer) > _MIN_SUSPICIOUS_LEN:
        flags.append("Unusually detailed for a conceptual question")

    # Flag 2: AI essay structure
    answer_lower = answer.lower()
    for pattern in _STRUCTURE_PATTERNS:
        if re.search(pattern, answer_lower):
            flags.append("Formal essay structure detected")
            break

    # Flag 3: filler word ratio
    filler_count = sum(1 for w in words if w.lower() in _FILLER_WORDS)
    if word_count > 20 and filler_count / word_count > _MAX_FILLER_RATIO:
        flags.append("High filler word ratio — possible padding")

    # Flag 4: perfect vocabulary at low depth
    technical_terms = re.findall(
        r'\b(algorithm|complexity|O\(n\)|paradigm|abstraction|polymorphism'
        r'|concurrency|asynchronous|idempotent|immutable)\b',
        answer_lower
    )
    if depth == 1 and len(technical_terms) >= 3:
        flags.append("Advanced terminology unexpected at depth 1")

    risk = "low"
    if len(flags) == 1: risk = "medium"
    if len(flags) >= 2: risk = "high"

    return {
        "flagged": len(flags) > 0,
        "flags":   flags,
        "risk":    risk
    }