import json
from app.core.llm import call_llm
from app.agents.extractor.prompts import outcome_sentence_selector_prompt


class OutcomeSentenceSelector:
    def select(self, sentences):
        if not sentences:
            return []

        payload = [
            {"sentence_id": s.sentence_id, "text": s.text}
            for s in sentences
        ]

        prompt = outcome_sentence_selector_prompt(payload)
        response = call_llm(prompt)

        # 🔎 디버그 로그 (처음엔 꼭 켜두자)
        if not response or not response.strip():
            print("[OutcomeSentenceSelector] empty response")
            return []

        cleaned = response.strip()

        # 코드블록 제거 (```json ... ``` 방어)
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            # 혹시 json 태그가 있으면 제거
            cleaned = cleaned.replace("json", "", 1).strip()

        try:
            data = json.loads(cleaned)
            ids = data.get("selected_sentence_ids", [])
            if not isinstance(ids, list):
                return []
            return [sid for sid in ids if isinstance(sid, str)]
        except Exception as e:
            print("[OutcomeSentenceSelector] parse failed:", e)
            print("[OutcomeSentenceSelector] raw response:", response)
            return []