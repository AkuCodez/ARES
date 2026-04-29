# resume_engine/run_pipeline.py

from resume_engine.extract_text import extract_text_from_pdf
from resume_engine.skill_extractor import extract_skills
from resume_engine.schema import ResumeProfile
from resume_engine.skills import classify_skill
from resume_engine.evaluator import evaluate_answer, detect_overclaims, analyze_concepts
from resume_engine.questions import generate_question, select_skill_for_question
from resume_engine.interview_state import InterviewState
from resume_engine.policy import decide_next_level, compute_confidence, estimate_skill_depth


def run(resume_path: str):
    # ── 1. Extract raw text from PDF ──────────────────────────────────────
    resume_text = extract_text_from_pdf(resume_path)

    # ── 2. Extract skills + projects from resume text via LLM ─────────────
    raw_profile = extract_skills(resume_text)

    skills         = raw_profile.get("skills", {})
    projects       = raw_profile.get("projects", [])
    total_projects = max(len(projects), 1)   # avoid division by zero

    # ── 3. Estimate depth for each skill using resume evidence ─────────────
    #    FIX: was calling compute_confidence(info, total_projects) which is wrong —
    #    compute_confidence() works on interview history, not skill info.
    #    Depth estimation now uses estimate_skill_depth() from policy.py.
    for skill_name, info in skills.items():
        evidence_text = "\n".join(info.get("evidence", []))
        depth_result  = estimate_skill_depth(skill_name, evidence_text)

        # Store numeric starting level (1/2/3) — NOT the text label
        # FIX: this was the root cause of the "foundation" / "Beginner" string
        # being passed into generate_question() as depth
        info["depth_estimate"]  = depth_result.get("depth_estimate", "Intermediate")
        info["starting_level"]  = depth_result.get("starting_level", 1)

    # ── 4. Detect overclaims and append to risk flags ─────────────────────
    if "risk_flags" not in raw_profile:
        raw_profile["risk_flags"] = []

    raw_profile["risk_flags"].extend(detect_overclaims(raw_profile))

    # ── 5. Build typed profile object ─────────────────────────────────────
    profile = ResumeProfile(**raw_profile)

    # ── 6. Select opening skill + initialise interview state ───────────────
    #    FIX: select_skill_for_question() now takes (profile_dict, history)
    #    not just skills — and returns a skill name string
    first_skill = select_skill_for_question(raw_profile, history=[])

    #    FIX: depth_level must be an int (1/2/3), never a text string
    #    was: normalize_level(skills[skill]["depth_estimate"]) → returned strings
    #    now: read the starting_level int we stored in step 3
    starting_depth = skills.get(first_skill, {}).get("starting_level", 1)

    state = InterviewState(
        skill=first_skill,
        depth_level=starting_depth
    )

    return profile, state