# resume_engine/sharecard.py
import os
import json
from supabase import create_client

def get_client():
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_ANON_KEY")
    )

def save_result(profile, interview_state, gaps) -> str:
    """Serialize session → insert → return UUID string."""
    history = interview_state.history
    profile_dict = vars(profile) if not isinstance(profile, dict) else profile

    payload = {
        "skills":   list(profile_dict.get("skills", {}).keys()),
        "history":  [
            {
                "question": t["question"],
                "answer":   t["answer"],
                "skill":    t.get("skill",""),
                "depth":    t.get("depth", 1),
                "quality":  t["quality"]
            }
            for t in history
        ],
        "gaps":     gaps or [],
        "verdict_counts": interview_state.verdict_counts,
    }
    client = get_client()
    res = client.table("results").insert({"payload": payload}).execute()
    return res.data[0]["id"]  # UUID


def fetch_result(uuid: str) -> dict | None:
    """Fetch result by UUID. Returns payload dict or None."""
    client = get_client()
    res = client.table("results").select("payload").eq("id", uuid).execute()
    if res.data:
        return res.data[0]["payload"]
    return None