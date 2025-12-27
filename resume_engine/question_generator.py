import random
from resume_engine.question_templates import QUESTION_TEMPLATES

def generate_question(skill: str, depth_level: str, asked_questions: set) -> str:
    """
    Generate a question based on current interview depth level.
    """
    candidates = QUESTION_TEMPLATES[depth_level]

    # Avoid repeating questions
    unused = [
        q for q in candidates
        if q.format(skill=skill) not in asked_questions
    ]

    if not unused:
        unused = candidates  # fallback

    template = random.choice(unused)
    return template.format(skill=skill)
