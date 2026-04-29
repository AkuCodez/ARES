# resume_engine/interview_state.py

class InterviewState:
    def __init__(self, skill, depth_level):
        self.current_skill = skill
        self.depth_level   = self._parse_depth(depth_level)  # ← always an int
        self.turn          = 0
        self.history       = []
        self.asked_questions = set()

    @staticmethod
    def _parse_depth(depth) -> int:
        """Always store depth_level as int 1-3, regardless of what comes in."""
        _TEXT_MAP = {
            "beginner":     1, "foundation": 1, "basic":    1,
            "intermediate": 2, "applied":    2, "moderate": 2,
            "advanced":     3, "expert":     3, "deep":     3,
        }
        try:
            return max(1, min(int(depth), 3))
        except (ValueError, TypeError):
            return _TEXT_MAP.get(str(depth).lower().strip(), 1)

    def record(self, question, answer, quality):
        self.history.append({
            "question": question,
            "answer":   answer,
            "quality":  quality
        })
        self.asked_questions.add(question)
        self.turn += 1