from __future__ import annotations
from typing import List, Dict

def claim_extraction_prompt(sentence: list[dict], focus_instruction: str = None) -> str:
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