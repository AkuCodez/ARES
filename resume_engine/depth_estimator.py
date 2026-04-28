# resume_engine/depth_estimator.py

from resume_engine.llm_client import client, MODEL
import json

DEPTH_PROMPT = """
You are a senior technical interviewer evaluating a candidate's skill depth.

Given a skill name and evidence from their resume, return JSON ONLY:
{
  "depth_estimate": "Beginner | Intermediate | Advanced | Expert",
  "reason": "<one sentence explaining the rating>"
}

Rules:
- Beginner: knows syntax, basic usage only
- Intermediate: has used it in real projects with some complexity
- Advanced: handles edge cases, optimizations, architectural decisions
- Expert: deep internals knowledge, can teach or design systems around it
- Be conservative — most candidates are Intermediate at best
"""

def estimate_skill_depth(skill_name: str, evidence_text: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": DEPTH_PROMPT},
            {
                "role": "user",
                "content": f"Skill: {skill_name}\nEvidence from resume:\n{evidence_text}"
            }
        ],
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)