# app/agents/extractor/claim_filter.py

import json
from app.agents.extractor.prompts import CLAIM_FILTER_PROMPT
from app.core.llm import call_llm


class ClaimFilter:
    """
    Decide whether a claim should be kept for downstream processing.
    """

    def filter(self, claim: str, section: str) -> dict:
        prompt = CLAIM_FILTER_PROMPT.format(
            claim=claim,
            section=section,
        )

        response = call_llm(prompt)

        try:
            result = json.loads(response)
            if result["decision"] not in ("keep", "discard"):
                raise ValueError("invalid decision")
            return result
        except Exception:
            # 안전장치: 애매하면 버린다
            return {
                "decision": "discard",
                "reason": "parse_error",
            }
