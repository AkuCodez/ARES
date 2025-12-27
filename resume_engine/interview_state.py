# resume_engine/interview_state.py

class InterviewState:
    def __init__(self, skill, depth_level):
        self.current_skill = skill
        self.depth_level = depth_level
        self.turn = 0
        self.history = []
        self.asked_questions = set()

    def record(self, question, answer, quality):
        self.history.append({
            "question": question,
            "answer": answer,
            "quality": quality
        })
        self.asked_questions.add(question)
        self.turn += 1
