# resume_engine/concept_bootstrapper.py

import json
from resume_engine.llm_client import client, MODEL

SYSTEM_PROMPT = """
You are a senior technical interviewer.

List 5–7 core concepts expected from someone who knows this skill.

Return JSON only:
{
  "concepts": [string]
}
"""

def bootstrap_concepts(skill: str) -> list:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Skill: {skill}"}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)
    return data.get("concepts", [])
