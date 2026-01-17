"""
Search Agent Prompts
Prompt templates for arXiv paper search and relevance filtering
"""

# Prompt for converting user query + analysis_goal into arXiv search query
SEARCH_QUERY_GENERATION_PROMPT = """You are an expert at converting research questions into effective arXiv search queries.

User's Question: {content}
Analysis Goal: {analysis_goal}

Task: Generate a concise, effective arXiv search query (2-10 keywords) that will find relevant academic papers.

Guidelines:
- Focus on technical terms and key concepts
- Use academic/scientific terminology
- Avoid common words and articles
- Keep it focused and specific

Respond with ONLY the search query, no explanations.

Search Query:"""


# Prompt for evaluating paper relevance
RELEVANCE_EVALUATION_PROMPT = """You are an expert at evaluating research paper relevance.

User's Research Interest:
- Question: {content}
- Analysis Goal: {analysis_goal}

Paper Information:
- Title: {title}
- Abstract: {abstract}

Task: Evaluate how relevant this paper is to the user's research interest.

Respond with ONLY a JSON object in this exact format:
{{"relevance_score": 0.85, "reason": "brief explanation"}}

The relevance_score should be between 0.0 (not relevant) and 1.0 (highly relevant)."""


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
