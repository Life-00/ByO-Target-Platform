# app/agents/extractor/prompts.py
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


    Below are sentences extracted from a research paper.
    Each sentence may come from any section (methods, results, discussion, conclusion, etc.).

    Your task:
    - Identify ONLY sentences that are directly relevant to the claim.
    - Classify each selected sentence by its ROLE.

    Roles:
    - support: empirical, experimental, or analytical statements supporting the claim
    - limitation: statements that qualify, restrict, or weaken the claim

    Sentences:
    \"\"\"{sentences}\"\"\"


    Return STRICT JSON only in the following format:

    {{
      "evidence_spans": [
        {{
          "sentence_id": string,
          "role": "support" | "limitation"
        }}
      ]
    }}

    Guidelines:
    - Do NOT rely on section names to determine relevance.
    - Judge based on semantic relation to the claim.
    - Do NOT introduce new claims.
    - If no relevant sentences exist, return an empty list.
    """.strip()

def outcome_sentence_selector_prompt(sentences):
    numbered = "\n".join(
        f"{i+1}. ({s['sentence_id']}) {s['text']}"
        for i, s in enumerate(sentences)
    )

    return f"""
    You are selecting outcome sentences from a scientific paper.
    
    STRICT RULES:
    - Return ONLY valid JSON.
    - Do NOT include explanations, markdown, or code fences.
    - If no sentence qualifies, return an empty list.
    
    Select ONLY sentences that explicitly report study results.
    Do NOT infer, summarize, or rephrase.
    
    Sentences:
    {numbered}
    
    Return EXACTLY this JSON format:
    {{
      "selected_sentence_ids": []
    }}
    """

def outcome_claim_builder_prompt(sentences):
    numbered = "\n".join(
        f"- ({s['sentence_id']}) {s['text']}"
        for s in sentences
    )

    return f"""
    You are generating ONE conservative outcome claim.
    
    Rules:
    - Use ONLY the information explicitly stated in the sentences.
    - Do NOT add new interpretations or mechanisms.
    - Do NOT generalize beyond the sentences.
    - The claim must describe an outcome or association.
    
    Sentences:
    {numbered}
    
    Return JSON only:
    {{
      "claim": "...",
      "confidence": 0.6,
      "evidence_level": "observational"
    }}
    """



CLAIM_FILTER_PROMPT = """
You are evaluating whether a sentence represents a core research claim
or merely background information in a scientific paper.

Sentence:
"{claim}"

Context:
- Section: {section}

Guidelines:
- Discard if the sentence states general epidemiology, prevalence,
  well-known background facts, or introductory context.
- Keep if the sentence reports research findings, associations,
  effects, outcomes, or conclusions derived from the study.

Respond in JSON only:

{{
  "decision": "keep" | "discard",
  "reason": "background" | "epidemiology" | "general_fact" | "core_finding"
}}
"""

CLAIM_TYPE_PROMPT = """
Classify the following scientific claim into one of the categories:

- background: general context, prior knowledge, epidemiology
- method: study design, data, analysis methods
- outcome: results, effects, associations, conclusions

Claim:
"{claim}"

Respond in JSON only:

{{
  "type": "background" | "method" | "outcome"
}}
"""

