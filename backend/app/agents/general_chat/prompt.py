"""
General Chat Agent Prompts
Prompt templates and instructions for general chat agent
"""

# Default system prompt for general chat with optional RAG capability
SYSTEM_PROMPT = """You are a helpful and intelligent AI assistant.

Your role:
- Engage in natural, helpful conversations on any topic
- When documents are provided, use them as reference to support your answers
- Always respond in Korean (한국어로 답변하세요)

Guidelines:
- Be conversational and friendly for general questions
- Use document context when available and relevant
- Be clear, concise, and accurate
- Admit when you don't know something
- Maintain natural conversation flow"""

# Document context template
DOCUMENT_CONTEXT_TEMPLATE = """Based on the following context documents:

{document_context}

Please help with the following request."""

# Analysis goal template
ANALYSIS_GOAL_TEMPLATE = """Please perform the following analysis: {analysis_goal}

Use the context documents to support your analysis."""

# Few-shot examples
FEW_SHOT_EXAMPLES = [
    {
        "question": "What is machine learning?",
        "answer": "Machine learning is a subset of artificial intelligence (AI) that focuses on enabling computer systems to learn and improve from experience without being explicitly programmed. It involves training algorithms on data to identify patterns and make predictions."
    },
    {
        "question": "Explain this concept in simple terms",
        "answer": "I'll break this down into simple, easy-to-understand points that build on each other, avoiding technical jargon where possible."
    }
]

# Configuration constants
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048
MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 2.0
MIN_MAX_TOKENS = 100
MAX_MAX_TOKENS = 4096
