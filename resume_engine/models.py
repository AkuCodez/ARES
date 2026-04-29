# resume_engine/models.py
#
# Merged from: schema.py, interview_state.py
#
# Public API:
#   SkillInfo       — dataclass for a single skill entry
#   ResumeProfile   — dataclass for the full extracted resume
#   InterviewState  — stateful interview session tracker

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# 1. Schema  (from schema.py)
# ─────────────────────────────────────────────

@dataclass
class SkillInfo:
    """
    Represents a single skill extracted from the resume.

    Attributes:
        confidence:     0.0–1.0 — how strongly the resume supports this skill
        depth_estimate: text label e.g. "Beginner", "Intermediate", "Advanced"
        starting_level: numeric interview depth to start at (1, 2, or 3)
        evidence:       list of resume snippets that justify the skill claim
    """
    confidence:     float
    depth_estimate: str
    starting_level: int   = 1
    evidence:       list  = field(default_factory=list)


@dataclass
class ResumeProfile:
    """
    Full parsed profile of a candidate, built from their resume.

    Attributes:
        skills:     dict mapping skill name -> SkillInfo
        projects:   list of project name strings found in the resume
        risk_flags: list of overclaim / thin-evidence warning strings
    """
    skills:     dict  = field(default_factory=dict)
    projects:   list  = field(default_factory=list)
    risk_flags: list  = field(default_factory=list)


# ─────────────────────────────────────────────
# 2. Interview state  (from interview_state.py)
# ─────────────────────────────────────────────

class InterviewState:
    """
    Tracks all mutable state for a single interview session.

    Attributes:
        current_skill:   skill currently being tested
        depth_level:     current question depth (always int 1-3)
        turn:            number of Q&A turns completed
        history:         list of turn dicts
        asked_questions: set of question strings already asked
    """

    _TEXT_TO_LEVEL: dict = {
        "beginner":     1,
        "foundation":   1,
        "basic":        1,
        "novice":       1,
        "intermediate": 2,
        "applied":      2,
        "moderate":     2,
        "advanced":     3,
        "expert":       3,
        "deep":         3,
        "senior":       3,
    }

    def __init__(self, skill: str, depth_level):
        self.current_skill   = skill
        self.depth_level     = self._parse_depth(depth_level)
        self.turn            = 0
        self.history         = []
        self.asked_questions = set()

    @classmethod
    def _parse_depth(cls, depth) -> int:
        """
        Convert any depth value to a valid int between 1 and 3.
        Handles ints, numeric strings ("1"), and text labels ("Beginner").
        This is the permanent fix for the "foundation" / str crash bug.
        """
        try:
            return max(1, min(int(depth), 3))
        except (ValueError, TypeError):
            return cls._TEXT_TO_LEVEL.get(str(depth).lower().strip(), 1)

    def record(self, question: str, answer: str, quality: dict) -> None:
        """
        Record a completed Q&A turn.

        Args:
            question: The question that was asked
            answer:   The candidate's raw answer text
            quality:  Full evaluation dict from evaluator.evaluate_answer()
        """
        self.history.append({
            "question": question,
            "answer":   answer,
            "quality":  quality,
            "skill":    self.current_skill,  # needed by select_skill_for_question
            "depth":    self.depth_level,    # useful for final analytics
        })
        self.asked_questions.add(question)
        self.turn += 1

    # ── Convenience properties ─────────────────────────────────────────────

    @property
    def last_quality(self) -> Optional[str]:
        """Verdict string from the most recent turn, or None if no turns yet."""
        if not self.history:
            return None
        return self.history[-1].get("quality", {}).get("quality")

    @property
    def verdict_counts(self) -> dict:
        """Count of each verdict: {"strong": n, "okay": n, "weak": n}"""
        counts = {"strong": 0, "okay": 0, "weak": 0}
        for turn in self.history:
            v = turn.get("quality", {}).get("quality", "weak")
            counts[v] = counts.get(v, 0) + 1
        return counts