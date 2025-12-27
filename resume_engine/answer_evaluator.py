# resume_engine/answer_evaluator.py

from resume_engine.llm_answer_evaluator import evaluate_with_llm
from resume_engine.concept_analyzer import analyze_concepts

def evaluate_answer(skill: str, question: str, answer: str) -> dict:
    llm_eval = evaluate_with_llm(skill, question, answer)
    concept_eval = analyze_concepts(skill, answer)

    verdict = llm_eval.get("verdict", "weak")

    return {
        "quality": verdict,
        "scores": {
            "correctness": llm_eval["correctness"],
            "depth": llm_eval["depth"],
            "clarity": llm_eval["clarity"]
        },
        "concepts": concept_eval,
        "feedback": llm_eval["feedback"]
    }
