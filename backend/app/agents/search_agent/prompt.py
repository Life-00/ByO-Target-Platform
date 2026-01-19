"""
Search Agent Prompts
Prompt templates for arXiv paper search and relevance filtering
"""

# Prompt for converting user query + analysis_goal into arXiv search query
SEARCH_QUERY_GENERATION_PROMPT = """You are an expert at converting research questions into effective arXiv search queries.

User's Question: {content}
Analysis Goal: {analysis_goal}

Task: Generate a concise, effective arXiv search query (2-6 core keywords) optimized for academic paper search.

CRITICAL RULES for Academic Paper Search:
1. Use SIMPLE, CONCRETE terms that actually appear in paper titles/abstracts
2. AVOID meta-analysis terms: "compare", "comparison", "safety profile", "evaluation", "review"
3. Use SPECIFIC scientific terminology:
   - For toxicity: "toxicity", "liver injury", "hepatotoxicity", "adverse events", "ALT", "AST"
   - For mechanisms: "mechanism", "pathway", "binding", "inhibition"
   - For drug names: use exact compound names or generic names
4. Break down complex questions into their CORE CONCEPTS only
5. If question asks for "comparison", just include the main entities (e.g., "HER2 inhibitor hepatotoxicity" NOT "compare HER2 inhibitors")

BAD Examples (too ambitious, won't find papers):
❌ "HER2 inhibitors" AND "hepatotoxicity" COMPARE "approved therapies"
❌ "SAFETY PROFILES" "neratinib" "tucatinib"
❌ "compare efficacy" "immunotherapy" "chemotherapy"

GOOD Examples (simple, concrete terms):
✅ HER2 inhibitor hepatotoxicity
✅ neratinib liver toxicity
✅ immunotherapy melanoma
✅ CRISPR gene editing safety

Respond with ONLY the search query (2-6 keywords), no explanations or quotes.

Search Query:"""


# Enhanced prompt for comprehensive paper evaluation
ENHANCED_RELEVANCE_EVALUATION_PROMPT = """You are an expert research evaluator specializing in biomedical literature.

User's Research Interest:
- Question: {content}
- Analysis Goal: {analysis_goal}

Paper Information:
- Title: {title}
- Abstract: {abstract}

Task: Evaluate this paper across THREE dimensions:

1. RELEVANCE: How directly related is this paper to the user's research question?
2. RELIABILITY: How trustworthy and well-documented is this research?
3. COVERAGE: What specific aspects of the research question does this paper address?

Respond with ONLY a JSON object in this exact format:
{{
    "relevance_score": 0.85,
    "reliability_indicators": {{
        "has_experimental_data": true,
        "has_numerical_results": true,
        "methodology_clear": true,
        "is_preprint": false
    }},
    "coverage_aspects": ["in_vitro", "dose_response", "mechanism"],
    "overall_reason": "brief explanation"
}}

Scores should be between 0.0 and 1.0."""


# Prompt for extracting requested paper count from user input
REQUESTED_COUNT_EXTRACTION_PROMPT = """Analyze the user's question and extract how many papers they want to find.

User's Question: {content}

Examples:
- "파킨슨병 관련 논문 하나만 찾아줘" → 1
- "transformer 논문 3개 찾아줘" → 3
- "딥러닝 논문 찾아줘" → 5 (default when not specified)
- "몇 개 논문 보여줘" → 5 (default for ambiguous requests)

Respond with ONLY a JSON object:
{{"requested_count": <number>}}

The number must be between 1 and 20. If not specified or unclear, use 5."""


# Configuration
DEFAULT_MAX_RESULTS = 5
DEFAULT_MIN_RELEVANCE = 0.7
ARXIV_API_BASE_URL = "http://export.arxiv.org/api/query"
