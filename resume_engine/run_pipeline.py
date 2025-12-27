# resume_engine/run_pipeline.py

from resume_engine.extract_text import extract_text_from_pdf
from resume_engine.skill_extractor import extract_skills
from resume_engine.schema import ResumeProfile
from resume_engine.overclaim_detector import detect_overclaims
from resume_engine.confidence_scorer import compute_confidence
from resume_engine.skill_graph import SkillGraph

from resume_engine.question_selector import select_skill_for_question
from resume_engine.question_generator import generate_question
from resume_engine.interview_state import InterviewState
from resume_engine.answer_evaluator import evaluate_answer
from resume_engine.next_question_policy import decide_next_level


def run(resume_path: str):
    resume_text = extract_text_from_pdf(resume_path)
    raw_profile = extract_skills(resume_text)

    skills = raw_profile.get("skills", {})
    projects = raw_profile.get("projects", [])
    total_projects = len(projects)

    for skill, info in skills.items():
        info["confidence"] = compute_confidence(info, total_projects)

    raw_profile["risk_flags"].extend(
        detect_overclaims(raw_profile)
    )

    # graph = SkillGraph(
    #     uri="bolt://localhost:7687",
    #     user="neo4j",
    #     password="Shivam131204@"
    # )
    # graph.build_graph(skills.keys())
    # graph.close()

    profile = ResumeProfile(**raw_profile)

    # 🔥 START INTERVIEW
    skill = select_skill_for_question(skills)
    from resume_engine.next_question_policy import normalize_level

    state = InterviewState(
        skill=skill,
        depth_level=normalize_level(
            skills[skill]["depth_estimate"]
        )
    )


    # print(f"\nInterview started on skill: {skill}\n")

    # for _ in range(3):  # 3-turn interview
    #     question = generate_question(
    #         state.current_skill,
    #         skills[state.current_skill],
    #         state.asked_questions
    #     )

    #     print("Q:", question)

    #     answer = input("A: ")
        
    #     evaluation = evaluate_answer(
    #         state.current_skill,
    #         question,
    #         answer
    #     )

    #     quality = evaluation["quality"]

    #     state.record(question, answer, evaluation)

    #     print(f"[Interviewer verdict: {quality}]")
    #     print(f"[Feedback: {evaluation['feedback']}]")

    #     concepts = evaluation.get("concepts")
    #     if concepts and concepts["coverage"] is not None:
    #         print(
    #             f"[Concept coverage: "
    #             f"{len(concepts['mentioned'])}/"
    #             f"{len(concepts['mentioned']) + len(concepts['missing'])}]"
    #         )
    #         if concepts["missing"]:
    #             print(f"[Missing concepts: {', '.join(concepts['missing'])}]")

    #     state.depth_level = decide_next_level(
    #         state.depth_level,
    #         quality
    #     )

    #     print(f"[Next depth level: {state.depth_level}]\n")

    return profile, state

# if __name__ == "__main__":
#     profile, state = run("data/Akshaj Tiwari_Resume.pdf")

#     print("\n=== Interview Summary ===")
#     for turn in state.history:
#         print(turn)
