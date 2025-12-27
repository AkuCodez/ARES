# resume_engine/skill_graph.py

from neo4j import GraphDatabase
from resume_engine.skill_ontology import SKILL_RELATIONS

class SkillGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def add_skill(self, tx, skill, known):
        tx.run(
            """
            MERGE (s:Skill {name: $skill})
            SET s.known = $known
            """,
            skill=skill,
            known=known
        )

    def add_relation(self, tx, src, rel, dst):
        tx.run(
            f"""
            MATCH (a:Skill {{name: $src}})
            MATCH (b:Skill {{name: $dst}})
            MERGE (a)-[:{rel}]->(b)
            """,
            src=src,
            dst=dst
        )

    def build_graph(self, extracted_skills):
        with self.driver.session(database="neo4j") as session:
            for skill in extracted_skills:
                is_known = skill in SKILL_RELATIONS

                session.execute_write(
                    self.add_skill, skill, is_known
                )

                if is_known:
                    for prereq in SKILL_RELATIONS[skill]["prerequisites"]:
                        session.execute_write(self.add_skill, prereq, True)
                        session.execute_write(
                            self.add_relation, skill, "REQUIRES", prereq
                        )

                    for sub in SKILL_RELATIONS[skill]["subskills"]:
                        session.execute_write(self.add_skill, sub, True)
                        session.execute_write(
                            self.add_relation, skill, "HAS_SUBSKILL", sub
                        )
