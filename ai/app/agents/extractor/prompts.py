# app/agents/extractor/prompts.py
from __future__ import annotations


def claim_detection_prompt(sentence: str) -> str:
    """
    Step 1. Claim Detection
    - Binary decision + rewrite
    """
    return f"""
    You are a scientific information extractor.
    
    Task:
    Decide whether the sentence below is an independent scientific claim.
    
    Definition:
    - A claim asserts a relationship, effect, association, or experimental finding.
    - Background information, definitions, or general descriptions are NOT claims.
    
    Sentence:
    \"\"\"{sentence}\"\"\"
    
    Output rules:
    - If NOT a claim: output exactly "NO"
    - If a claim: rewrite it as a concise, standalone claim (one sentence).
    - Do NOT add information not present in the sentence.
    """.strip()


def entity_extraction_prompt(
    claim: str,
    disease_hint: str | None = None,
    target_hint: str | None = None,
) -> str:
    """
    Step 2. Entity Extraction (JSON only)
    """
    hints = []
    if disease_hint:
        hints.append(f'DISEASE_HINT: "{disease_hint}"')
    if target_hint:
        hints.append(f'TARGET_HINT: "{target_hint}"')

    hint_block = "\n".join(hints) if hints else "NONE"

    return f"""
    You are a scientific entity extractor.
    
    Task:
    Extract the primary TARGET and DISEASE explicitly mentioned in the claim.
    - If an entity is not explicitly stated, return null.
    - Do NOT guess or infer unstated entities.
    - Use hints only if they are clearly supported by the claim text.
    
    Hints:
    {hint_block}
    
    Claim:
    \"\"\"{claim}\"\"\"
    
    Return STRICT JSON only:
    {{
      "target": string | null,
      "disease": string | null
    }}
    """.strip()


def relation_inference_prompt(claim: str) -> str:
    """
    Step 3. Relation & Evidence Inference (JSON only)
    """
    return f"""
    You are a scientific relation annotator.
    
    Task:
    Infer structured relation labels from the claim below.
    
    Important:
    - Confidence refers to your confidence in the extraction labels,
      NOT the truth of the scientific claim.
    - If information is unclear, use "unknown" and lower confidence.
    
    Claim:
    \"\"\"{claim}\"\"\"
    
    Return STRICT JSON only:
    {{
      "stance": "support" | "refute" | "neutral" | "unknown",
      "effect": "increase" | "decrease" | "no_change" | "mixed" | "unknown",
      "evidence_level": "in_vitro" | "in_vivo" | "clinical" | "review" | "unknown",
      "confidence": number
    }}
    """.strip()
