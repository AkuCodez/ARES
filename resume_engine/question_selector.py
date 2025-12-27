# resume_engine/question_selector.py

def select_skill_for_question(skills: dict) -> str:
    """
    Pick the most interview-relevant skill.
    Strategy: lowest confidence but non-trivial skill.
    """
    ranked = sorted(
        skills.items(),
        key=lambda x: x[1]["confidence"]
    )

    for skill, info in ranked:
        if info["confidence"] < 0.7:
            return skill

    # fallback
    return ranked[0][0]
