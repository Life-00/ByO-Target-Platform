"""
Embedding Agent Prompts
Prompt templates and instructions for document embedding agent
"""

# Summary generation prompt (Korean)
SUMMARY_PROMPT = """다음 문서의 핵심 요약을 300-500단어의 한국어로 작성해주세요. 
주요 내용, 핵심 결과, 중요한 발견사항을 포함하세요.
문서의 구조와 흐름을 명확하게 유지하면서, 가독성 좋게 작성해주세요.

===== 문서 내용 =====
{text}

===== 요약 ====="""

# Chunk analysis prompt
CHUNK_ANALYSIS_PROMPT = """Analyze the following text chunk and extract:
1. Main topics covered
2. Key concepts
3. Important entities (if any)
4. Relevance score (1-10)

Text:
{chunk}"""

# Document quality assessment prompt
DOCUMENT_QUALITY_PROMPT = """Assess the quality and content of this document chunk:
- Is it well-structured?
- Does it contain useful information?
- Are there any issues (OCR errors, formatting problems)?
- What is the quality score (1-10)?

Text:
{chunk}"""

# Configuration constants
DEFAULT_CHUNK_SIZE = 500
MIN_CHUNK_SIZE = 100
MAX_CHUNK_SIZE = 2000
DEFAULT_SUMMARY_LENGTH = 400
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_SUMMARY_TOKENS = 1000

# Chunking strategy
CHUNKING_STRATEGY = "word_based"  # Can be: word_based, sentence_based, semantic

# Summary generation settings
SUMMARY_MIN_LENGTH = 200
SUMMARY_MAX_LENGTH = 600
SUMMARY_LANGUAGE = "ko"  # Korean

# Embedding settings
EMBEDDING_MODEL = "solar-1-mini-chat"
EMBEDDING_BATCH_SIZE = 10
MAX_CHUNKS_PER_DOCUMENT = 100
