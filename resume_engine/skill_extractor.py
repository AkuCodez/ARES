# resume_engine/skill_extractor.py

from openai import OpenAI
import streamlit as st
import os
import json

api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


SYSTEM_PROMPT = """
You are a senior technical interviewer and resume analyzer.

Return STRICT JSON in the following format ONLY.
DO NOT add markdown, backticks, or explanations.

{
  "skills": {
    "<skill_name>": {
      "confidence": <float between 0 and 1>,
      "depth_estimate": "Beginner | Intermediate | Advanced | Expert",
      "evidence": [<list of strings>]
    }
  },
  "projects": [<list of strings>],
  "risk_flags": [<list of strings>]
}

Rules:
- Only include skills that have evidence in projects or experience.
- Be conservative in confidence and depth.
- Penalize vague or over-claimed skills.
"""

def clean_json_output(text: str) -> str:
    """
    Defensive cleaning in case model returns markdown accidentally
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
    return text.strip()

def extract_skills(resume_text: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": resume_text}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}  # 🔒 FORCE JSON
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
