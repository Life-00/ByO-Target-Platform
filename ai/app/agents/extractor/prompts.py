# app/agents/extractor/prompts.py

from __future__ import annotations
from typing import List, Dict

def claim_extraction_prompt(sentence: list[dict]) -> str:
    return f"""
    You are a scientific information extractor.
    
    Task:
    From the given sentence, extract a SINGLE scientific claim if present.
    If the sentence is purely descriptive or methodological, still extract the claim as-is.
    
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