import json
from app.core.llm import call_llm
from app.agents.extractor.prompts import outcome_claim_builder_prompt
from app.agents.extractor.parser import ExtractedClaim


class ConservativeOutcomeClaimBuilder:
    def build(self, sentences):
        """
        sentences: List[SectionSentence]
        return: ExtractedClaim | None
        """

        if not sentences:
            return None

        payload = [
            {
                "sentence_id": s.sentence_id,
                "text": s.text,
            }
            for s in sentences
        ]

        prompt = outcome_claim_builder_prompt(payload)
        response = call_llm(prompt)

        try:
            data = json.loads(response)
            return ExtractedClaim(**data)
        except Exception as e:
            print("[OutcomeClaimBuilder] parse failed:", e)
            return None