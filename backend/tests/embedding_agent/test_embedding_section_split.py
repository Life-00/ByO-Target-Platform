# tests/embedding_agent/test_embedding_section_split.py

import asyncio
from pathlib import Path

from app.agents.embedding_agent.agent import EmbeddingAgent
from app.services.embedding_service import EmbeddingService


TEST_PDF_PATH = Path(
    r"C:\Users\twili\Documents\upstage-workspace\test\ByO-Target-Platform\backend\tests\embedding_agent\Breast cancer -  Biology, biomarkers, and treatments.pdf"
)


async def run_test():
    agent = EmbeddingAgent(
        db=None,  # ✅ DB 제거
        embedding_service=EmbeddingService()
    )

    full_text, page_texts = await agent.extract_text(str(TEST_PDF_PATH))

    # 🔍 1단계: LLM 섹션 분해
    sections = await agent.split_into_sections_with_llm(full_text)

    print("\n[TEST] Section titles:")
    for sec in sections:
        print("-", sec["section_title"])

    # 🔍 2단계: 섹션별 chunking
    for sec in sections:
        chunks = await agent.chunk_text(sec["text"])
        print(
            f"[TEST] Section={sec['section_title']} chunks={len(chunks)}"
        )


if __name__ == "__main__":
    asyncio.run(run_test())
