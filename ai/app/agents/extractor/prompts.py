# app/agents/extractor/prompts.py

from __future__ import annotations


def extract_claims_prompt(abstract: str) -> str:
    return f"""
    You are an expert scientific information extractor.
    
    Given the following abstract, extract the key scientific claims.
    Each claim should be a concise, standalone statement.
    
    Abstract:
    \"\"\"{abstract}\"\"\"
    
    Return STRICT JSON only:
    {{
      "claims": [
        {{
          "claim": string,
          "source_sentence_id": number
        }}
      ]
    }}
    """.strip()


def relation_inference_prompt(claim: str) -> str:
    return f"""
    You are an expert scientific reasoning model.
    
    Analyze the following claim and extract structured relational information.
    
    Guidelines:
    - Preserve the semantic nuance of the claim.
    - Only constrain effect_direction and evidence_level to the allowed values.
    - confidence reflects your confidence in this structured extraction, not factual truth.
    
    Claim:
    \"\"\"{claim}\"\"\"
    
    Return STRICT JSON only:
    {{
      "stance_description": string,
      "effect_direction": "increase | decrease | modulate | no_significant_effect | unknown",
      "effect_descriptor": string | null,
      "outcome_measure": string | null,
      "evidence_level": "in_vitro | in_vivo | clinical | review | unknown",
      "confidence": number
    }}
    """.strip()