# resume_engine/skill_extractor.py

from resume_engine.llm_client import client, MODEL
import json

SYSTEM_PROMPT = """
You are a senior technical interviewer and resume analyzer.

Return STRICT JSON in the following format ONLY.
DO NOT add markdown, backticks, or explanations.

{
  "skills": {
    "<skill_name>": {
      "confidence": <float between 0 and 1>,
      "depth_estimate": "Beginner | Intermediate | Advanced | Expert",
      "evidence": [<list of strings describing where this skill was used>]
    }
  },
  "projects": [<list of project name strings>],
  "risk_flags": [<list of warning strings>]
}

Rules:
- Only include skills that have evidence in projects or experience.
- Be conservative in confidence and depth.
- Penalize vague or over-claimed skills.
"""

def clean_json_output(text: str) -> str:
    """Strip markdown code fences if model accidentally adds them."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()

def extract_skills(resume_text: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": resume_text}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("LLM returned empty response")

    content = clean_json_output(content)

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print("FAILED JSON OUTPUT:\n", content)
        raise e