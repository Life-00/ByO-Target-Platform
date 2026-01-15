from __future__ import annotations
from typing import List, Dict

def claim_extraction_prompt(sentence: list[dict], focus_instruction: str = None) -> str:
    """
    Phase 1: Claim-Extractor (Abstract 기반)
    """

    focus_prompt = ""
    if focus_instruction:
        focus_prompt = f"""
    IMPORTANT FOCUS:
    The user is specifically looking for information related to: "{focus_instruction}".
    - Prioritize claims that match this focus.
    - If a sentence is irrelevant to this focus, you may skip extracting it or mark it as low salience.
    """

    return f"""
    You are a scientific information extractor.
    
    Task:
    From the given sentence, extract a SINGLE scientific claim if present.
    If the sentence is purely descriptive or methodological, still extract the claim as-is.
    {focus_prompt}
    
    Then analyze the claim along the following dimensions.
    
    Sentence:
    \"\"\"{sentence}\"\"\"
    
    Return STRICT JSON only with the following structure:
    
    {{
      "claim": string,
    
      "effect": {{
        "direction": string | null,
        "target_outcome": string | null,
        "rationale": string | null,
        "confidence": number | null
      }},
    
      "stance": {{
        "polarity": string,
        "strength": string,
        "conditions": string | null
      }},
    
      "salience": {{
        "level": string,
        "reason": string
      }},
    
      "evidence_level": string,
      "confidence": number,
      "notes": string | null
    }}
    
    Guidelines:
    - Do NOT infer beyond the sentence.
    - Use natural language for direction, polarity, strength, and level.
    - If no effect is stated, set effect fields to null.
    - Salience levels should reflect importance within the paper (high / medium / low).
    - Evidence level examples: review, clinical, preclinical, unknown.
    - Confidence should reflect how explicit the claim is.
    """.strip()


def evidence_extraction_prompt(
    claim: str,
    sentences: list[dict],
) -> str:
    """
    Phase 2: Evidence-Extractor (Results / Discussion 기반)
    """
    return f"""
    You are a scientific evidence extractor.
    
    Given the following CLAIM:
    \"\"\"{claim}\"\"\"
    
    From the provided sentences, identify ONLY sentences that are directly relevant.
    
    Sentence roles:
    - support: empirical or experimental results that support the claim
    - limitation: statements that qualify, restrict, or limit the claim
    
    Sentences:
    \"\"\"{sentences}\"\"\"
    
    Return STRICT JSON only in the following format:
    
    {{
      "evidence_spans": [
        {{
          "sentence_id": string,
          "role": "support" | "limitation" # 주장 지지 ? or 조건/한계 존재?
        }}
      ]
    }}
    
    Guidelines:
    - Do NOT introduce new claims.
    - Do NOT paraphrase sentences.
    - Select sentences based on role, not section importance.
    - If no relevant sentences exist, return an empty list.
    """.strip()

