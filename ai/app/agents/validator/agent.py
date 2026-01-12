from __future__ import annotations

from app.schemas.fact import FactSet
from app.schemas.claim import ValidatedClaims
from app.agents.validator.graph import build_validator_graph

class ValidatorAgent:
    def __init__(self):
        self.graph = build_validator_graph()

    def run(self, fact_set: FactSet) -> ValidatedClaims:
        """
        Main entry point using LangGraph.
        """
        init_state = {
            "fact_set": fact_set
        }
        
        final_state = self.graph.invoke(init_state)
        return final_state["validated_claims"]
