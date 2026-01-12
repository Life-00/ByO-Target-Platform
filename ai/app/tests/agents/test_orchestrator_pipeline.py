from app.agents.orchestrator.agent import OrchestratorAgent
from app.schemas.user_query import UserQuery

def test_orchestrator_full_pipeline():

    agent = OrchestratorAgent()

    uq = UserQuery(
        query_id="test",
        target="EGFR",
        disease="lung cancer",
        question="Is EGFR a valid therapeutic target?"
    )

    state = agent.run(user_query=uq)

    assert "validated_claims" in state
    assert "target_dossier" in state