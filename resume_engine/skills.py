# resume_engine/skills.py
#
# Merged from: skill_concepts.py, skill_ontology.py, skill_registry.py,
#              dynamic_concept_store.py, concept_bootstrapper.py
#
# Public API:
#   SKILL_CONCEPTS                          -> dict  (static concept map)
#   SKILL_RELATIONS                         -> dict  (prerequisite/subskill graph)
#   classify_skill(skill)                   -> "known" | "unknown"
#   load_dynamic_concepts()                 -> dict
#   save_dynamic_concepts(data)             -> None
#   get_concepts_for_skill(skill)           -> list[str]  (static + dynamic + bootstrap)
#   bootstrap_concepts(skill)               -> list[str]  (LLM-generated, then cached)

import json
from pathlib import Path

from resume_engine.llm_client import client, MODEL


# ─────────────────────────────────────────────
# 1. Static concept map
#    What core concepts should a candidate know for each skill?
#    Expand this list as you add more skills to the system.
# ─────────────────────────────────────────────

SKILL_CONCEPTS: dict = {
    # Web fundamentals
    "HTML": [
        "elements", "tags", "attributes", "semantic html", "forms",
        "accessibility", "meta tags"
    ],
    "CSS": [
        "selectors", "box model", "flexbox", "grid",
        "responsive design", "specificity", "pseudo-classes"
    ],
    "JavaScript": [
        "variables", "functions", "closures", "async",
        "event loop", "promises", "dom manipulation", "prototypes"
    ],
    "React.js": [
        "components", "props", "state", "hooks",
        "virtual dom", "useEffect", "context api", "reconciliation"
    ],
    "Node.js": [
        "event loop", "async io", "modules", "npm",
        "express", "streams", "middleware", "callbacks"
    ],

    # Languages
    "Python": [
        "data types", "functions", "classes", "decorators",
        "generators", "list comprehensions", "modules", "exception handling"
    ],
    "Java": [
        "oop", "inheritance", "interfaces", "generics",
        "collections", "multithreading", "jvm", "memory management"
    ],
    "C++": [
        "pointers", "memory management", "templates",
        "stl", "raii", "virtual functions", "move semantics"
    ],
    "TypeScript": [
        "type annotations", "interfaces", "generics",
        "type inference", "union types", "enums", "strict mode"
    ],

    # AI / ML
    "Machine Learning": [
        "data preprocessing", "model training", "overfitting",
        "evaluation metrics", "bias variance tradeoff",
        "cross validation", "feature engineering"
    ],
    "Deep Learning": [
        "neural networks", "backpropagation", "activation functions",
        "cnn", "rnn", "loss functions", "optimizers", "batch normalization"
    ],
    "Natural Language Processing": [
        "tokenization", "embeddings", "transformers", "attention",
        "bert", "fine tuning", "named entity recognition", "text classification"
    ],
    "Computer Vision": [
        "convolutional neural networks", "image preprocessing",
        "object detection", "transfer learning", "data augmentation",
        "feature maps", "pooling"
    ],

    # Data
    "SQL": [
        "select", "joins", "aggregations", "indexes",
        "transactions", "normalization", "subqueries", "views"
    ],
    "MongoDB": [
        "documents", "collections", "queries", "aggregation pipeline",
        "indexes", "schema design", "replication", "sharding"
    ],
    "Pandas": [
        "dataframe", "series", "indexing", "groupby",
        "merge", "pivot", "missing values", "apply"
    ],

    # DevOps / Cloud
    "Docker": [
        "containers", "images", "dockerfile", "volumes",
        "networking", "docker compose", "registry", "layers"
    ],
    "AWS": [
        "ec2", "s3", "lambda", "iam",
        "vpc", "rds", "cloudwatch", "load balancing"
    ],
    "Git": [
        "commits", "branches", "merge", "rebase",
        "pull requests", "conflict resolution", "stash", "tags"
    ],

    # System design & backend
    "System Design": [
        "scalability", "load balancing", "caching", "database sharding",
        "microservices", "message queues", "cap theorem", "consistency"
    ],
    "REST API": [
        "http methods", "status codes", "endpoints", "authentication",
        "rate limiting", "versioning", "json", "idempotency"
    ],
    "Flask": [
        "routes", "blueprints", "request context", "jinja2",
        "middleware", "error handlers", "sqlalchemy", "testing"
    ],
    "FastAPI": [
        "path operations", "pydantic models", "dependency injection",
        "async", "openapi", "authentication", "background tasks"
    ],
}


# ─────────────────────────────────────────────
# 2. Skill ontology
#    Prerequisites and subskills for known skills.
#    Used by the (optional) Neo4j skill graph feature.
# ─────────────────────────────────────────────

SKILL_RELATIONS: dict = {
    "Machine Learning": {
        "prerequisites": ["Python", "Statistics", "Pandas"],
        "subskills":     ["Scikit-Learn", "XGBoost", "Model Evaluation"]
    },
    "Deep Learning": {
        "prerequisites": ["Machine Learning", "Python"],
        "subskills":     ["CNN", "RNN", "Transformers"]
    },
    "Natural Language Processing": {
        "prerequisites": ["Deep Learning", "Python"],
        "subskills":     ["Transformers", "BERT", "Text Classification"]
    },
    "Computer Vision": {
        "prerequisites": ["Deep Learning", "Python"],
        "subskills":     ["CNN", "Object Detection", "Image Segmentation"]
    },
    "React.js": {
        "prerequisites": ["JavaScript", "HTML", "CSS"],
        "subskills":     ["Redux", "React Router", "Next.js"]
    },
    "Node.js": {
        "prerequisites": ["JavaScript"],
        "subskills":     ["Express", "REST API", "WebSockets"]
    },
    "FastAPI": {
        "prerequisites": ["Python", "REST API"],
        "subskills":     ["Pydantic", "SQLAlchemy", "OAuth2"]
    },
    "Flask": {
        "prerequisites": ["Python", "REST API"],
        "subskills":     ["Jinja2", "SQLAlchemy", "Flask-Login"]
    },
    "Docker": {
        "prerequisites": ["Linux basics"],
        "subskills":     ["Docker Compose", "Container Networking", "Multi-stage Builds"]
    },
    "AWS": {
        "prerequisites": ["Networking basics", "Linux basics"],
        "subskills":     ["EC2", "S3", "Lambda", "RDS"]
    },
    "System Design": {
        "prerequisites": ["REST API", "SQL", "Networking basics"],
        "subskills":     ["Load Balancing", "Caching", "Message Queues"]
    },
}


# ─────────────────────────────────────────────
# 3. Skill registry
#    Quick lookup: is this skill already understood by the system?
# ─────────────────────────────────────────────

def classify_skill(skill: str) -> str:
    """
    Returns 'known' if the system has static data for this skill,
    'unknown' if it will need to be bootstrapped via LLM.
    """
    if skill in SKILL_CONCEPTS or skill in SKILL_RELATIONS:
        return "known"
    return "unknown"


# ─────────────────────────────────────────────
# 4. Dynamic concept store
#    LLM-bootstrapped concepts are cached in a local JSON file
#    so we don't call the API on every resume upload.
# ─────────────────────────────────────────────

_DYNAMIC_STORE_PATH = Path("resume_engine/dynamic_concepts.json")


def load_dynamic_concepts() -> dict:
    """Load cached dynamic concepts from disk. Returns {} if file doesn't exist."""
    if not _DYNAMIC_STORE_PATH.exists():
        return {}
    try:
        return json.loads(_DYNAMIC_STORE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_dynamic_concepts(data: dict) -> None:
    """Persist dynamic concepts to disk."""
    _DYNAMIC_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _DYNAMIC_STORE_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ─────────────────────────────────────────────
# 5. Concept bootstrapper
#    For skills not in SKILL_CONCEPTS, ask the LLM to generate
#    a concept list and cache it so we don't repeat the call.
# ─────────────────────────────────────────────

_BOOTSTRAP_PROMPT = """
You are a senior technical interviewer.

Given a skill name, list 6-8 core concepts a candidate should know
to demonstrate solid working knowledge of this skill.

Return JSON ONLY — no markdown, no explanation:
{
  "concepts": ["concept1", "concept2", ...]
}

Rules:
- Concepts must be specific technical terms, not vague phrases
- Think: what would you actually probe in a 30-minute interview?
- All concepts in lowercase
"""


def bootstrap_concepts(skill: str) -> list:
    """
    Use the LLM to generate concepts for an unknown skill.
    Result is cached in dynamic_concepts.json — LLM is only called once per skill.
    """
    dynamic = load_dynamic_concepts()

    # Return from cache if already bootstrapped — no API call needed
    if skill in dynamic:
        return dynamic[skill]

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _BOOTSTRAP_PROMPT},
            {"role": "user", "content": f"Skill: {skill}"}
        ],
        temperature=0.2,
        response_format={"type": "json_object"}
    )

    data     = json.loads(response.choices[0].message.content)
    concepts = data.get("concepts", [])

    # Cache so this API cost is only ever paid once per unknown skill
    dynamic[skill] = concepts
    save_dynamic_concepts(dynamic)

    return concepts


# ─────────────────────────────────────────────
# 6. Unified concept lookup  ← use this everywhere
#    Static map → disk cache → LLM bootstrap, in that order.
# ─────────────────────────────────────────────

def get_concepts_for_skill(skill: str) -> list:
    """
    Retrieve concepts for any skill, using the fastest available source:
      1. SKILL_CONCEPTS  — instant, no I/O
      2. dynamic cache   — fast, disk read only
      3. bootstrap_concepts — one-time LLM call, then cached forever

    Use this instead of importing SKILL_CONCEPTS directly so unknown
    skills are handled automatically without crashing.
    """
    if skill in SKILL_CONCEPTS:
        return SKILL_CONCEPTS[skill]

    dynamic = load_dynamic_concepts()
    if skill in dynamic:
        return dynamic[skill]

    return bootstrap_concepts(skill)