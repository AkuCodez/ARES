from resume_engine.llm_client import client, MODEL
import json

def estimate_skill_depth(skill_name, evidence_text):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": DEPTH_PROMPT},
            {
                "role": "user",
                "content": f"""
Skill: {skill_name}
Evidence from resume:
{evidence_text}
"""
            }
        ],
        temperature=0.1
    )
    return json.loads(response.choices[0].message.content)
