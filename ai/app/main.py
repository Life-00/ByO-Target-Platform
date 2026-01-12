# 시스템 로직 시작점
# DialogueAgent 생성
# 내부 흐름 제어

# app/main.py
from app.agents.dialogue.agent import DialogueAgent
from app.schemas.message import UserMessage


def run():
    agent = DialogueAgent()

    while True:
        msg = input("USER > ")
        response = agent.handle(
            UserMessage(session_id="demo", message=msg)
        )
        print(f"SYSTEM ({response.type}) > {response.message}")