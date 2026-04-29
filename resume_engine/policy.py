# resume_engine/policy.py
#
# Merged from: depth_estimator.py, next_question_policy.py, confidence_scorer.py
#
# Public API:
#   estimate_skill_depth(skill, evidence)    -> dict
#   decide_next_level(current_depth, quality)-> int
#   compute_confidence(history)              -> dict

import json
from resume_engine.llm_client import client, MODEL


# ─────────────────────────────────────────────
# 1. Depth estimator
#    Given a skill and resume evidence, ask LLM to estimate
#    how deep the candidate's knowledge actually is.
#    BUG FIX: DEPTH_PROMPT was referenced but never defined — fixed here.
# ─────────────────────────────────────────────

_DEPTH_PROMPT = """
You are a senior technical interviewer analyzing a candidate's resume.

Given a skill name and supporting evidence from the candidate's resume,
estimate their actual depth of knowledge for that skill.

Return JSON ONLY — no markdown, no explanation:
{
  "depth_estimate": "Beginner | Intermediate | Advanced | Expert",
  "starting_level": <1 | 2 | 3>,
  "reason": "<one sentence justifying the estimate>"
}

Depth definitions:
  Beginner     -> knows syntax and basic usage, no real project use. starting_level: 1
  Intermediate -> has used it in real projects with moderate complexity.  starting_level: 1
  Advanced     -> handles edge cases, optimizations, architectural use.   starting_level: 2
  Expert       -> deep internals, can design systems around it.           starting_level: 3

Rules:
- Be CONSERVATIVE. Most students are Beginner or Intermediate.
- A skill listed on a resume without project evidence = Beginner.
- Do not reward vague evidence like "familiar with" or "exposure to".
- starting_level tells the interview engine where to BEGIN questioning.
"""


def estimate_skill_depth(skill: str, evidence_text: str) -> dict:
    """
    Estimate the depth of a candidate's knowledge for a given skill
    based on resume evidence.

    Args:
        skill:         e.g. "Machine Learning", "React.js"
        evidence_text: raw text of resume evidence for this skill

    Returns:
        {
            "depth_estimate": "Beginner | Intermediate | Advanced | Expert",
            "starting_level": 1 | 2 | 3,
            "reason": str
        }
    """
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": _DEPTH_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Skill: {skill}\n"
                        f"Resume evidence:\n{evidence_text or 'No evidence provided.'}"
                    )
                }
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    except Exception as e:
        print(f"[policy] depth estimation failed for '{skill}': {e}")
        # Safe fallback — start everyone at level 1
        return {
            "depth_estimate": "Intermediate",
            "starting_level": 1,
            "reason": "Depth estimation unavailable — defaulting to Intermediate."
        }


# ─────────────────────────────────────────────
# 2. Next question policy
#    After each answer, decide whether to go deeper (harder),
#    stay at the same level, or step back (easier).
#
#    Depth scale:
#      1 = Conceptual  (What is X? Why does it exist?)
#      2 = Applied     (How did you use X in your project?)
#      3 = Deep dive   (Trade-offs, internals, system design)
# ─────────────────────────────────────────────

# How much to adjust depth based on verdict
_DEPTH_DELTA: dict = {
    "strong": +1,   # nailed it → go harder
    "okay":    0,   # reasonable → hold steady
    "weak":   -1,   # struggled  → ease off
}

_MIN_DEPTH = 1
_MAX_DEPTH = 3

def _safe_depth(depth) -> int:
    """Convert any depth value to a valid int between 1 and 3."""
    try:
        return max(1, min(int(depth), 3))
    except (ValueError, TypeError):
        return 1

def decide_next_level(current_depth: int, quality: str) -> int:
    """
    Adjust interview depth based on the quality of the last answer.

    Args:
        current_depth: Current depth level (1, 2, or 3)
        quality:       Verdict string — "weak", "okay", or "strong"

    Returns:
        New depth level, clamped between 1 and 3
    """
    current_depth      = _safe_depth(current_depth)
    quality_normalised = quality.strip().lower()
    delta  = _DEPTH_DELTA.get(quality_normalised, 0)
    new_depth = current_depth + delta
    return max(_MIN_DEPTH, min(_MAX_DEPTH, new_depth))


# ─────────────────────────────────────────────
# 3. Confidence scorer
#    After the interview, compute an overall performance summary
#    from the full history of verdicts and scores.
# ─────────────────────────────────────────────

# Numeric value assigned to each verdict for averaging
_VERDICT_WEIGHTS: dict = {
    "strong": 1.0,
    "okay":   0.5,
    "weak":   0.0,
}

# Hire recommendation thresholds (based on weighted average)
_HIRE_THRESHOLDS: dict = {
    "Strong Yes":        0.75,
    "Yes":               0.55,
    "Borderline":        0.35,
    "Needs Improvement": 0.0,
}


def compute_confidence(history: list) -> dict:
    """
    Compute an overall confidence score and hire recommendation
    from the full interview history.

    Args:
        history: List of turn dicts from InterviewState.history
                 Each turn must have: "quality" -> {"quality": str, "scores": dict}

    Returns:
        {
            "overall_score":      float,   # 0.0 – 1.0
            "hire_recommendation": str,
            "verdict_breakdown":  dict,    # {"strong": n, "okay": n, "weak": n}
            "avg_scores":         dict,    # {"correctness": f, "depth": f, "clarity": f}
            "trend":              str,     # "improving" | "declining" | "stable"
        }
    """
    if not history:
        return {
            "overall_score":       0.0,
            "hire_recommendation": "Needs Improvement",
            "verdict_breakdown":   {"strong": 0, "okay": 0, "weak": 0},
            "avg_scores":          {"correctness": 0.0, "depth": 0.0, "clarity": 0.0},
            "trend":               "stable"
        }

    # ── Verdict breakdown ──────────────────────────────────────────────
    verdict_breakdown = {"strong": 0, "okay": 0, "weak": 0}
    weighted_sum = 0.0

    for turn in history:
        verdict = turn.get("quality", {}).get("quality", "weak").lower()
        verdict_breakdown[verdict] = verdict_breakdown.get(verdict, 0) + 1
        weighted_sum += _VERDICT_WEIGHTS.get(verdict, 0.0)

    overall_score = weighted_sum / len(history)

    # ── Average dimension scores ───────────────────────────────────────
    dims = {"correctness": [], "depth": [], "clarity": []}
    for turn in history:
        scores = turn.get("quality", {}).get("scores", {})
        for dim in dims:
            val = scores.get(dim)
            if val is not None:
                dims[dim].append(val)

    avg_scores = {
        dim: round(sum(vals) / len(vals) / 10, 2) if vals else 0.0
        for dim, vals in dims.items()
    }

    # ── Performance trend (first half vs second half) ──────────────────
    mid = len(history) // 2
    if mid > 0:
        first_half  = history[:mid]
        second_half = history[mid:]

        def half_score(half):
            return sum(
                _VERDICT_WEIGHTS.get(t.get("quality", {}).get("quality", "weak").lower(), 0)
                for t in half
            ) / len(half)

        first_score  = half_score(first_half)
        second_score = half_score(second_half)
        gap = second_score - first_score

        if gap > 0.2:
            trend = "improving"
        elif gap < -0.2:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # ── Hire recommendation ────────────────────────────────────────────
    hire_recommendation = "Needs Improvement"
    for label, threshold in _HIRE_THRESHOLDS.items():
        if overall_score >= threshold:
            hire_recommendation = label
            break

    return {
        "overall_score":       round(overall_score, 2),
        "hire_recommendation": hire_recommendation,
        "verdict_breakdown":   verdict_breakdown,
        "avg_scores":          avg_scores,
        "trend":               trend
    }