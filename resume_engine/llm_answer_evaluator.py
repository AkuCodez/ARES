# resume_engine/llm_answer_evaluator.py

import json
from openai import OpenAI

client = OpenAI()

SYSTEM_PROMPT = """
You are a senior technical interviewer.

Evaluate the candidate answer STRICTLY and CONSERVATIVELY.

Return JSON ONLY in this format:

{
  "correctness": <0 to 10>,
  "depth": <0 to 10>,
  "clarity": <0 to 10>,
  "verdict": "weak | okay | strong",
  "feedback": "<short constructive feedback>"
}

Rules:
- Penalize vague or generic answers
- Penalize confident but incorrect statements
- Reward reasoning and examples
- Do NOT hallucinate missing knowledge
"""

def evaluate_with_llm(skill: str, question: str, answer: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
Skill: {skill}
Question: {question}
Candidate Answer: {answer}
"""
            }
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)
