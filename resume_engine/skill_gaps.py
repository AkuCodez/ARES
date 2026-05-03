# resume_engine/skill_gaps.py

import json
from resume_engine.llm_client import client, MODEL

_GAP_PROMPT = """
You are a senior engineer giving detailed career advice after a technical interview.

Return JSON ONLY:
{
  "gaps": [
    {
      "topic": "<specific topic>",
      "reason": "<why this matters based on their performance>",
      "what_to_learn": "<3-4 specific concepts to focus on>",
      "resource_name": "<resource title>",
      "resource_url": "<actual working URL>",
      "estimated_time": "<e.g. 2 hours, 1 week>",
      "priority": "high | medium | low",
      "priority_reason": "<why this priority — career impact explanation>"
    }
  ]
}

Rules:
- Max 5 gaps, ordered high → low priority
- Topics must be SPECIFIC: not "study Python" but "Python generators and memory-efficient iteration"
- resource_url must be a real URL — prefer:
    - Official docs (docs.python.org, reactjs.org, pytorch.org)
    - Free courses (cs50.harvard.edu, missing.csail.mit.edu)
    - Real Python (realpython.com)
    - roadmap.sh for skill paths
- priority_reason must explain career impact: hiring bar, foundational importance, frequency in interviews
"""

def generate_skill_gaps(history: list, profile: dict) -> list:
    """
    Analyze interview history and return personalized study recommendations.
    
    Returns list of gap dicts with topic, reason, resource, priority.
    """
    # Build compact performance summary for LLM
    summary = []
    for i, turn in enumerate(history, 1):
        q       = turn.get("quality", {})
        verdict = q.get("quality", "weak")
        missing = q.get("concepts", {}).get("missing", [])
        summary.append(
            f"Q{i} [{turn.get('skill')}] verdict={verdict}"
            + (f" missing={missing}" if missing else "")
        )

    skills_claimed = {
        s: info.get("depth_estimate", "?")
        for s, info in profile.get("skills", {}).items()
    }

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": _GAP_PROMPT},
                {"role": "user", "content":
                    f"Claimed skills: {skills_claimed}\n\n"
                    f"Interview performance:\n" + "\n".join(summary)
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content).get("gaps", [])
    except Exception as e:
        print(f"[skill_gaps] failed: {e}")
        return []