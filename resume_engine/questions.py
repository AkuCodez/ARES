# resume_engine/questions.py
#
# Merged from: question_generator.py, question_selector.py, question_templates.py
#
# Public API:
#   generate_question(skill, depth, asked, profile)  -> str
#   select_skill_for_question(profile, history)      -> str

import json
import random
from typing import Optional

from resume_engine.llm_client import client, MODEL


# ─────────────────────────────────────────────
# 1. Fallback template bank
#    Used ONLY when LLM call fails or profile has no project context.
#    Organised by depth: 1=surface, 2=applied, 3=deep internals
# ─────────────────────────────────────────────

_TEMPLATES: dict = {
    1: [
        "Can you explain what {skill} is and where you have used it?",
        "What is {skill} and why would someone choose to use it?",
        "Describe the core concept behind {skill} in your own words.",
        "What problem does {skill} solve?",
    ],
    2: [
        "Walk me through a specific project where you used {skill}. What decisions did you make?",
        "What challenges did you face when working with {skill} and how did you resolve them?",
        "How did you integrate {skill} with other technologies in your projects?",
        "Describe a bug or unexpected behavior you encountered with {skill} and how you debugged it.",
    ],
    3: [
        "What are the performance trade-offs you considered when using {skill}?",
        "How would you scale or optimize a system built with {skill} under heavy load?",
        "Explain an advanced feature or internals of {skill} that most beginners overlook.",
        "If you had to design a system that relied heavily on {skill}, what architectural decisions would you make?",
    ],
}

# ADD near top of questions.py
_PERSONAS = {
    "🏢 FAANG": """You are a senior FAANG interviewer at Google/Meta. 
Be technical, rigorous, and unforgiving. Always probe deeper — if they 
answer well, ask a harder follow-up. Focus on scalability, edge cases, 
and system design. Never accept vague answers.""",

    "🚀 Startup": """You are a startup CTO hiring a generalist engineer.
Ask about real shipping experience, not theory. Care about speed, 
pragmatic decisions, and breadth. Ask things like "how fast could you 
build X" or "what would you cut to ship faster".""",

    "🎓 Academic": """You are a CS professor conducting a viva voce exam.
Ask about theoretical foundations, formal definitions, time/space 
complexity, and first principles. Expect precise terminology. 
Challenge assumptions.""",

    "😊 Friendly": """You are a supportive senior engineer doing a casual 
technical chat. Keep tone warm. If candidate struggles, rephrase or 
give a small hint. Celebrate good answers. Make them feel comfortable.""",
}

# ADD to questions.py

_HINT_PROMPT = """
You are a helpful interviewer giving a subtle hint.
Give ONE short hint (1-2 sentences) that nudges toward the answer
WITHOUT revealing it directly.
Return JSON ONLY: {"hint": "<hint text>"}
"""

def generate_hint(skill: str, question: str) -> str:
    """Generate a subtle hint for the current question."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": _HINT_PROMPT},
                {"role": "user", "content": f"Skill: {skill}\nQuestion: {question}"}
            ],
            temperature=0.4,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content).get("hint", "")
    except Exception:
        return "Think about the core concept and a real example from your experience."
# ─────────────────────────────────────────────
# 2. Depth sanitizer
#    Guards against strings like "Beginner", "foundation", "1" etc.
#    being passed in as depth — always returns a clean int 1-3.
# ─────────────────────────────────────────────

def _safe_depth(depth) -> int:
    """Convert any depth value to a valid int between 1 and 3."""
    try:
        return max(1, min(int(depth), 3))
    except (ValueError, TypeError):
        return 1  # default to conceptual level


# ─────────────────────────────────────────────
# 3. Personalized LLM question generator
#    Reads the candidate's actual projects + evidence from the profile
#    and generates a question that references their real work.
# ─────────────────────────────────────────────

_QUESTION_PROMPT = """
You are a sharp, senior technical interviewer conducting a real interview.

You have the candidate's resume context below. Your job is to generate ONE
interview question for the given skill at the given depth level.

DEPTH LEVELS:
  1 = Conceptual   — test if they understand the fundamentals
  2 = Applied      — test if they can reason about their own project experience
  3 = Deep         — test internals, trade-offs, edge cases, system thinking

RULES:
- If the candidate has project evidence for this skill, reference their
  ACTUAL project name, feature, or implementation detail in the question.
  Make it feel like you read their resume — because you did.
- Do NOT ask questions already in the asked_questions list.
- Do NOT ask "Tell me about yourself" or anything generic.
- One question only. No preamble. No numbering. No quotation marks.
- The question must end with a question mark.
- Depth 1: start with "What", "How", "Can you explain", "Why"
- Depth 2: start with "Walk me through", "How did you", "What challenges"
- Depth 3: start with "How would you", "What trade-offs", "Explain why", "If you had to"

Return JSON ONLY:
{
  "question": "<the interview question>"
}
"""

def _extract_jd_skills(jd_text: str) -> list:
    """Pull key required skills from a job description."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content":
                    "Extract the top 5 technical skills required by this job description. "
                    "Return JSON ONLY: {\"skills\": [\"skill1\", ...]}"
                },
                {"role": "user", "content": jd_text}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content).get("skills", [])
    except Exception:
        return []

def _build_resume_context(skill: str, profile: Optional[dict], jd_text=None) -> str:
    if profile is not None and not isinstance(profile, dict):
        profile = vars(profile)
        
    if not profile:
        return f"Skill being tested: {skill}\nNo resume context available."

    lines = [f"Skill being tested: {skill}"]

    projects = profile.get("projects", [])
    if projects:
        lines.append(f"Candidate's projects: {', '.join(projects)}")

    skills_data = profile.get("skills", {})
    skill_info  = skills_data.get(skill, {})
    evidence    = skill_info.get("evidence", [])
    depth_label = skill_info.get("depth_estimate", "Unknown")
    confidence  = skill_info.get("confidence", 0)

    if evidence:
        lines.append(f"Evidence for {skill}:")
        for e in evidence[:4]:
            lines.append(f"  - {e}")

    lines.append(f"Claimed depth: {depth_label}  |  Confidence score: {confidence:.0%}")

    flags = profile.get("risk_flags", [])
    skill_flags = [f for f in flags if skill.lower() in f.lower()]
    if skill_flags:
        lines.append(f"⚠ Risk flags: {'; '.join(skill_flags)}")

    # ── JD context ───────────────────────────────────────────────────────
    if jd_text:
        jd_skills = _extract_jd_skills(jd_text)
        if jd_skills:
            lines.append(f"Job requires: {', '.join(jd_skills)}")
            lines.append("Prioritize questions relevant to the job requirements above.")

    return "\n".join(lines)




def _generate_with_llm(
    skill: str,
    depth: int,
    asked: tuple,
    profile: Optional[dict],
    jd_text = None,
    persona = None
) -> str:
    """Call LLM to generate a personalised interview question."""
    resume_context = _build_resume_context(skill, profile, jd_text)
    persona_line   = _PERSONAS.get(persona, _PERSONAS["😊 Friendly"])
    asked_list     = list(asked)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": persona_line},   
            {"role": "user",   "content": (
                f"{_QUESTION_PROMPT}\n\n"                  
                f"{resume_context}\n\n"
                f"Depth level: {depth}\n"
                f"Already asked:\n"
                + ("\n".join(f"  - {q}" for q in list(asked)) or "  None yet")
            )}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)
    return data.get("question", "").strip()


def _fallback_question(skill: str, depth, asked: tuple) -> str:
    """
    Template fallback used when LLM fails.
    Picks a random unused template at the right depth level.
    """
    depth_clamped = _safe_depth(depth)
    pool          = _TEMPLATES[depth_clamped]
    formatted     = [t.format(skill=skill) for t in pool]
    unused        = [q for q in formatted if q not in asked]
    return random.choice(unused) if unused else formatted[0]


# ─────────────────────────────────────────────
# 4. Main entry point — called by app.py
# ─────────────────────────────────────────────

def generate_question(
    skill: str,
    depth,
    asked: tuple,
    profile: Optional[dict] = None,
    jd_text= None,
    persona = None
) -> str:
    """
    Generate one interview question for a given skill and depth.

    Args:
        skill:   Skill being tested e.g. "Python", "Machine Learning"
        depth:   1 (conceptual) → 2 (applied) → 3 (deep internals)
                 Accepts int or str — sanitized internally via _safe_depth.
        asked:   Tuple of question strings already asked (to avoid repeats)
        profile: Full extracted resume profile dict. When provided, questions
                 are personalized to the candidate's actual projects.

    Returns:
        A single interview question string.
    """
    depth = _safe_depth(depth)   # sanitize once — protects both LLM and fallback paths

    try:
        question = _generate_with_llm(skill, depth, asked, profile, jd_text, persona)
        if question and question.endswith("?"):
            return question
        # LLM returned something malformed — fall through to template
        print(f"[questions] LLM returned malformed question for '{skill}', using fallback")
    except Exception as e:
        print(f"[questions] LLM generation failed for '{skill}': {e}")

    return _fallback_question(skill, depth, asked)


# ─────────────────────────────────────────────
# 5. Skill selector
# ─────────────────────────────────────────────

def select_skill_for_question(profile: dict, history: list) -> str:
    """
    Select the most appropriate skill to ask about next.

    Strategy (in priority order):
      1. Skills with evidence in projects (not just listed on resume)
      2. Skills that haven't been asked about yet
      3. Skills where the candidate last answered "weak" (re-probe)
      4. Highest confidence skill overall as final fallback
    """
    skills_data = profile.get("skills", {})

    if not skills_data:
        return "Python"

    asked_skills = {turn.get("skill") for turn in history if "skill" in turn}

    evidenced = {
        skill: info
        for skill, info in skills_data.items()
        if info.get("evidence")
    }
    pool = evidenced if evidenced else skills_data

    # Priority 1: unasked skills with evidence, ranked by confidence
    unasked = {s: i for s, i in pool.items() if s not in asked_skills}
    if unasked:
        return max(unasked, key=lambda s: unasked[s].get("confidence", 0))

    # Priority 2: re-probe last weak skill
    weak_turns = [
        t for t in history
        if t.get("quality", {}).get("quality") == "weak"
    ]
    if weak_turns:
        last_weak_skill = weak_turns[-1].get("skill")
        if last_weak_skill and last_weak_skill in skills_data:
            return last_weak_skill

    # Priority 3: highest confidence overall
    return max(pool, key=lambda s: pool[s].get("confidence", 0))

_FOLLOWUP_PROMPT = """
You are a technical interviewer. The candidate just answered a question
but missed some key concepts. Ask ONE sharp follow-up question that
specifically probes the missing concept — don't reveal the answer.

Return JSON ONLY: {"question": "<follow-up question>"}
"""

def generate_followup(skill: str, missing_concepts: list, last_answer: str) -> str:
    """Generate a targeted follow-up for missed concepts."""
    if not missing_concepts:
        return None
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": _FOLLOWUP_PROMPT},
                {"role": "user", "content":
                    f"Skill: {skill}\n"
                    f"Missing concepts: {', '.join(missing_concepts[:3])}\n"
                    f"Candidate's last answer: {last_answer}"
                }
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return data.get("question", "").strip() or None
    except Exception as e:
        print(f"[questions] follow-up generation failed: {e}")
        return None
    
# questions.py — ADD this, and pass jd_context into _build_resume_context
