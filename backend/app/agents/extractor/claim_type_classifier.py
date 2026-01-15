import json
from app.agents.extractor.prompts import CLAIM_TYPE_PROMPT
from app.core.llm import call_llm


class ClaimTypeClassifier:
    def classify(self, claim: str) -> str:
        prompt = CLAIM_TYPE_PROMPT.format(claim=claim)
        response = call_llm(prompt)

        try:
            result = json.loads(response)
            claim_type = result.get("type")
            if claim_type in ("background", "method", "outcome"):
                return claim_type
        except Exception:
            pass

        # 안전장치: 애매하면 outcome 아님으로 처리
        return "background"
