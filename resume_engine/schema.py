from pydantic import BaseModel
from typing import List, Dict

class SkillInfo(BaseModel):
    confidence: float
    depth_estimate: str
    evidence: List[str]
    #depth_reason: str

class ResumeProfile(BaseModel):
    skills: Dict[str, SkillInfo]
    projects: List[str]
    risk_flags: List[str]
