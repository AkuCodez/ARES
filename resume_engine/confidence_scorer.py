# resume_engine/confidence_scorer.py

def depth_to_score(depth: str) -> float:
    mapping = {
        "beginner": 0.4,
        "intermediate": 0.6,
        "advanced": 0.8,
        "expert": 0.9
    }
    return mapping.get(depth.lower(), 0.4)

def compute_confidence(skill_info: dict, total_projects: int) -> float:
    evidence = skill_info.get("evidence", [])
    depth = skill_info.get("depth_estimate", "Beginner")

    # 1️⃣ Evidence strength
    if len(evidence) == 0:
        evidence_score = 0.2
    elif len(evidence) == 1:
        evidence_score = 0.5
    else:
        evidence_score = 0.8

    # 2️⃣ Project coverage
    project_coverage = min(len(evidence) / max(total_projects, 1), 1.0)

    # 3️⃣ LLM quality signal
    depth_score = depth_to_score(depth)

    # 🔢 Weighted confidence
    confidence = (
        0.4 * evidence_score +
        0.3 * project_coverage +
        0.3 * depth_score
    )

    return round(confidence, 2)
