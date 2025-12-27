# resume_engine/skill_registry.py

from resume_engine.skill_concepts import SKILL_CONCEPTS
from resume_engine.skill_ontology import SKILL_RELATIONS

def classify_skill(skill: str) -> str:
    """
    Returns:
    - 'known' if system already understands this skill
    - 'unknown' otherwise
    """
    if skill in SKILL_CONCEPTS or skill in SKILL_RELATIONS:
        return "known"
    return "unknown"
