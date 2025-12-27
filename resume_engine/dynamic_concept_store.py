# resume_engine/dynamic_concept_store.py

import json
from pathlib import Path

FILE_PATH = Path("resume_engine/dynamic_concepts.json")

def load_dynamic_concepts():
    if not FILE_PATH.exists():
        return {}
    return json.loads(FILE_PATH.read_text())

def save_dynamic_concepts(data):
    FILE_PATH.write_text(json.dumps(data, indent=2))
