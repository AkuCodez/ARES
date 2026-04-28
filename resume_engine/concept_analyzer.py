# resume_engine/concept_analyzer.py

from resume_engine.skill_concepts import SKILL_CONCEPTS
from resume_engine.dynamic_concept_store import load_dynamic_concepts


def analyze_concepts(skill: str, answer: str) -> dict:
    dynamic = load_dynamic_concepts()
    concepts = SKILL_CONCEPTS.get(skill) or dynamic.get(skill)

    if not concepts:
        return {
            "coverage": None,
            "mentioned": [],
            "missing": []
        }

    answer_lower = answer.lower()

    # BUG FIX: both checks now use c.lower() so "Flexbox" matches "flexbox" etc.
    mentioned = [c for c in concepts if c.lower() in answer_lower]
    missing   = [c for c in concepts if c.lower() not in answer_lower]

    return {
        "coverage": len(mentioned) / len(concepts),
        "mentioned": mentioned,
        "missing": missing
    }