# resume_engine/overclaim_detector.py

from typing import Dict, List

TOOL_SKILLS = {
    "git", "github", "vscode", "postman", "docker"
}

def detect_overclaims(profile: Dict) -> List[str]:
    red_flags = []

    skills = profile.get("skills", {})
    projects = profile.get("projects", [])

    total_skills = len(skills)
    total_projects = max(len(projects), 1)

    # 🚩 Rule 1: Skill with no evidence (ignore tools)
    for skill, info in skills.items():
        if skill.lower() in TOOL_SKILLS:
            continue

        if not info.get("evidence"):
            red_flags.append(
                f"Skill '{skill}' listed without concrete project evidence."
            )

    # 🚩 Rule 2: Buzzword density (adjusted threshold)
    if total_skills / total_projects > 6:
        red_flags.append(
            "High number of skills compared to projects — possible buzzword overuse."
        )

    # 🚩 Rule 3: Depth inflation
    for skill, info in skills.items():
        depth = info.get("depth_estimate", "").lower()
        confidence = info.get("confidence", 0)

        if depth in ["advanced", "expert"] and confidence < 0.65:
            red_flags.append(
                f"Skill '{skill}' claims {depth} depth but evidence strength is low."
            )

    return red_flags
