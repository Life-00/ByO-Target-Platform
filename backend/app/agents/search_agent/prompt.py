"""
Search Agent Prompts
Prompt templates for Europe PMC (bioRxiv/medRxiv) search and relevance filtering
"""

# Prompt for converting user query + analysis_goal into Europe PMC search query
# app/agents/search_agent/prompt.py

SEARCH_QUERY_GENERATION_PROMPT = """Source: Senior Research Query Engineer.
Task: Generate a high-precision, single-line search query for Europe PMC based on the user's input.

User's Question: {content}

Guidelines:
1. IDENTIFY: Extract the most important nouns and technical terms from the user's question.
2. PRESERVE: Keep the original keywords from the question as the primary search terms.
3. EXPAND: Add 1-2 synonymous or related scientific terms only if they enhance the context of the original keywords.
4. FORMAT: Return ONLY the final keywords separated by spaces. 
   - NO numbers (1., 2.), NO bullet points, NO newlines.
   - NO quotes or special characters.
   - Limit to 3-5 terms in total.

Search Query:"""


# Prompt for evaluating paper relevance
RELEVANCE_EVALUATION_PROMPT = """Source: You are a Cold-Blooded Research Reviewer for Drug Discovery.
Context: Evaluating preprints for scientific evidence and experimental data.

Hypothesis/Goal: {analysis_goal}
User's Interest: {content}

Paper Title: {title}
Abstract: {abstract}

Task: Determine if this paper provides direct experimental evidence (e.g., p-values, binding data, specific assays) for the hypothesis.
- KEEP: Strong experimental evidence or direct mechanism validation.
- DROP: Purely theoretical, review-only, or irrelevant context.

Respond in JSON format:
{{"relevance_score": 0.0 to 1.0, "decision": "KEEP/DROP", "reason": "Specific evidence found or missing"}}"""


# Prompt for extracting requested paper count from user input
REQUESTED_COUNT_EXTRACTION_PROMPT = """Analyze the user's question and extract how many papers they want to find.

User's Question: {content}

Examples:
- "새로운 효소 설계 논문 1편만 찾아줘" -> 1
- "transformer 논문 3개 찾아줘" -> 3
- "최근 LLM 논문 찾아줘" -> 5 (default when not specified)
- "많이 찾아줘" -> 5 (default for ambiguous requests)

Respond with ONLY a JSON object:
{{"requested_count": <number>}}

The number must be between 1 and 20. If not specified or unclear, use 5."""


# Configuration
DEFAULT_MAX_RESULTS = 5
DEFAULT_MIN_RELEVANCE = 0.7

# Prompt for expanding a base search query into multiple variants
SEARCH_QUERY_EXPANSION_PROMPT = """Source: Search Query Optimization Expert.
Task: Expand the base query into a list of {count} distinct search variations.

Base Query: {base_query}

Guidelines:
- Rule 1: Every variation MUST retain at least one core keyword from the Base Query.
- Rule 2: Create variations by combining the core keywords with different scientific contexts (e.g., mechanism, pathology, interaction).
- Rule 3: Avoid leaning towards a specific sub-category unless mentioned in the Base Query.
- Rule 4: Return the result as a strict JSON list of strings.

Example Output: ["keyword1 keyword2", "keyword1 mechanism", "keyword2 interaction"]

Expanded Queries:"""

# Default number of expansions to try
DEFAULT_EXPANSION_COUNT = 3
