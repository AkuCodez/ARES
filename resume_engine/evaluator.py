# resume_engine/evaluator.py
#
# Merged from: llm_answer_evaluator.py, answer_evaluator.py,
#              concept_analyzer.py, overclaim_detector.py
#
# Public API (same as before — no changes needed in app.py or run_pipeline.py):
#   evaluate_answer(skill, question, answer) -> dict
#   detect_overclaims(profile)              -> list[str]
#   analyze_concepts(skill, answer)         -> dict

import json
from typing import Dict, List

from resume_engine.llm_client import client, MODEL
from resume_engine.skills import get_concepts_for_skill



# ─────────────────────────────────────────────
# 1. LLM-based answer evaluation
# ─────────────────────────────────────────────

_EVALUATOR_PROMPT = """
You are a senior technical interviewer.

Evaluate the candidate answer STRICTLY and CONSERVATIVELY.

Return JSON ONLY in this format:
{
  "correctness": <0 to 10>,
  "depth":       <0 to 10>,
  "clarity":     <0 to 10>,
  "verdict":     "weak | okay | strong",
  "feedback":    "<short constructive feedback, 1-2 sentences>"
}

Rules:
- Penalize vague or generic answers heavily
- Penalize confident but incorrect statements
- Reward concrete reasoning, examples, and trade-off awareness
- Do NOT hallucinate missing knowledge
- "strong" requires correctness >= 7 AND depth >= 6
- "weak"   requires correctness <= 4 OR depth <= 3
- Everything else is "okay"
"""

def _evaluate_with_llm(skill: str, question: str, answer: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _EVALUATOR_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Skill: {skill}\n"
                    f"Question: {question}\n"
                    f"Candidate Answer: {answer}"
                )
            }
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)


# ─────────────────────────────────────────────
# 2. Concept-level coverage analysis
# ─────────────────────────────────────────────

def analyze_concepts(skill: str, answer: str) -> dict:
    """
    Check which expected concepts for a skill appear in the candidate's answer.
    Falls back to dynamically bootstrapped concepts if skill isn't in static map.

    Returns:
        {
            "coverage":  float | None,   # fraction of concepts mentioned
            "mentioned": list[str],       # concepts the candidate covered
            "missing":   list[str]        # concepts they missed
        }
    """
    concepts = get_concepts_for_skill(skill)


    if not concepts:
        return {"coverage": None, "mentioned": [], "missing": []}

    answer_lower = answer.lower()

    # BUG FIX: both checks use .lower() — "Flexbox" now matches "flexbox"
    mentioned = [c for c in concepts if c.lower() in answer_lower]
    missing   = [c for c in concepts if c.lower() not in answer_lower]

    return {
        "coverage":  round(len(mentioned) / len(concepts), 2),
        "mentioned": mentioned,
        "missing":   missing
    }


# ─────────────────────────────────────────────
# 3. Main evaluation entry point
# ─────────────────────────────────────────────

def evaluate_answer(skill: str, question: str, answer: str) -> dict:
    """
    Full answer evaluation — combines LLM scoring with concept coverage.

    Returns:
        {
            "quality":   "weak | okay | strong",
            "scores":    {"correctness": int, "depth": int, "clarity": int},
            "concepts":  {"coverage": float, "mentioned": [...], "missing": [...]},
            "feedback":  str
        }
    """
    llm_eval     = _evaluate_with_llm(skill, question, answer)
    concept_eval = analyze_concepts(skill, answer)

    return {
        "quality": llm_eval.get("verdict", "weak"),
        "scores": {
            "correctness": llm_eval.get("correctness", 0),
            "depth":       llm_eval.get("depth", 0),
            "clarity":     llm_eval.get("clarity", 0)
        },
        "concepts": concept_eval,
        "feedback": llm_eval.get("feedback", "")
    }


# ─────────────────────────────────────────────
# 4. Overclaim detection (runs on full profile)
# ─────────────────────────────────────────────

_TOOL_SKILLS = {"git", "github", "vscode", "postman", "docker", "figma", "notion"}

def detect_overclaims(profile: Dict) -> List[str]:
    """
    Scan the extracted resume profile for suspicious skill claims.
    Returns a list of human-readable warning strings.

    Checks:
        1. Skills with no project evidence (ignores tool-skills like Git)
        2. Too many skills relative to number of projects (buzzword inflation)
        3. High depth claims (Advanced/Expert) with low confidence scores
    """
    red_flags = []
    skills   = profile.get("skills", {})
    projects = profile.get("projects", [])

    total_skills   = len(skills)
    total_projects = max(len(projects), 1)

    # Rule 1: skill listed with no supporting evidence
    for skill, info in skills.items():
        if skill.lower() in _TOOL_SKILLS:
            continue
        if not info.get("evidence"):
            red_flags.append(
                f"'{skill}' is listed without concrete project evidence."
            )

    # Rule 2: too many skills relative to projects
    if total_skills / total_projects > 6:
        red_flags.append(
            f"{total_skills} skills across {total_projects} project(s) — "
            "possible buzzword inflation."
        )

    # Rule 3: depth inflation — claims Advanced/Expert but evidence is thin
    for skill, info in skills.items():
        depth      = info.get("depth_estimate", "").lower()
        confidence = info.get("confidence", 0)

        if depth in ("advanced", "expert") and confidence < 0.65:
            red_flags.append(
                f"'{skill}' claims {depth}-level depth "
                f"but evidence confidence is only {confidence:.0%}."
            )

    return red_flags


def apply_hint_penalty(evaluation: dict) -> dict:
    """Reduce clarity score by 2 if hint was used."""
    evaluation = dict(evaluation)
    scores = dict(evaluation.get("scores", {}))
    scores["clarity"] = max(0, scores.get("clarity", 0) - 2)
    evaluation["scores"] = scores
    evaluation["feedback"] = "[Hint used] " + evaluation.get("feedback", "")
    return evaluation