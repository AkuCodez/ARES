# resume_engine/skill_graph.py
#
# Neo4j skill graph — OPTIONAL feature.
# skill_graph is disabled by default because neo4j is not a required dependency.
# To enable: pip install neo4j and set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# in your .env file, then uncomment the SkillGraph usage in run_pipeline.py.

import os

NEO4J_AVAILABLE = False

try:
    from neo4j import GraphDatabase
    from resume_engine.skill_ontology import SKILL_RELATIONS
    NEO4J_AVAILABLE = True
except ImportError:
    pass  # neo4j not installed — that's fine, feature is optional


class SkillGraph:
    def __init__(self):
        if not NEO4J_AVAILABLE:
            raise RuntimeError(
                "neo4j package is not installed. "
                "Run: pip install neo4j  to enable skill graph features."
            )
        uri      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user     = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_skill(self, tx, skill, known):
        tx.run(
            "MERGE (s:Skill {name: $skill}) SET s.known = $known",
            skill=skill, known=known
        )

    def add_relation(self, tx, src, rel, dst):
        tx.run(
            f"""
            MATCH (a:Skill {{name: $src}})
            MATCH (b:Skill {{name: $dst}})
            MERGE (a)-[:{rel}]->(b)
            """,
            src=src, dst=dst
        )

    def build_graph(self, extracted_skills):
        with self.driver.session(database="neo4j") as session:
            for skill in extracted_skills:
                is_known = skill in SKILL_RELATIONS
                session.execute_write(self.add_skill, skill, is_known)

                if is_known:
                    for prereq in SKILL_RELATIONS[skill]["prerequisites"]:
                        session.execute_write(self.add_skill, prereq, True)
                        session.execute_write(self.add_relation, skill, "REQUIRES", prereq)

                    for sub in SKILL_RELATIONS[skill]["subskills"]:
                        session.execute_write(self.add_skill, sub, True)
                        session.execute_write(self.add_relation, skill, "HAS_SUBSKILL", sub)