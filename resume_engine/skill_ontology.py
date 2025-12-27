# resume_engine/skill_ontology.py

SKILL_RELATIONS = {
    "Machine Learning": {
        "prerequisites": ["Python", "Statistics"],
        "subskills": ["Scikit-Learn", "XGBoost", "Model Evaluation"]
    },
    "Scikit-Learn": {
        "prerequisites": ["Python"],
        "subskills": ["Regression", "Classification"]
    },
    "XGBoost": {
        "prerequisites": ["Scikit-Learn"],
        "subskills": ["Boosting"]
    },
    "Deep Learning": {
        "prerequisites": ["Machine Learning"],
        "subskills": ["Neural Networks", "CNN"]
    }
}
