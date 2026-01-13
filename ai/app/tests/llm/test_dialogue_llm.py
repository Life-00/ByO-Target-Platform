from app.agents.dialogue.agent import DialogueAgent
from app.schemas.message import UserMessage

def test_dialogue_llm_result_smoke():
    agent = DialogueAgent()

    resp = agent.run(
        UserMessage(
            session_id="test-session",
            message="EGFR의 폐암 치료 타깃 가능성을 검증해줘",
            context={"text":"EGFR의 폐암 치료 타깃 가능성을 검증해줘"}
        )
    )

    assert resp.type in {"result", "question"}
    assert isinstance(resp.message, str)
    assert len(resp.message) > 0
