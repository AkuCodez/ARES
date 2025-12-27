# resume_engine/next_question_policy.py

DEPTH_ORDER = ["foundation", "intermediate", "advanced"]

def normalize_level(level: str) -> str:
    """
    Convert skill depth labels to question depth labels.
    """
    level = level.lower()

    if level == "beginner":
        return "foundation"
    if level in ["intermediate", "advanced"]:
        return level

    # fallback safety
    return "foundation"

def decide_next_level(current_level: str, quality: str) -> str:
    current_level = normalize_level(current_level)
    idx = DEPTH_ORDER.index(current_level)

    if quality == "strong" and idx < len(DEPTH_ORDER) - 1:
        return DEPTH_ORDER[idx + 1]

    if quality == "weak" and idx > 0:
        return DEPTH_ORDER[idx - 1]

    return current_level
