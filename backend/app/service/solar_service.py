from app.core.config import settings
from openai import OpenAI
import time

class SolarService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.UPSTAGE_API_KEY,
            base_url=settings.UPSTAGE_BASE_URL
        )

    async def perform_analysis(self, message: str, files: list):
        print(f"[{time.strftime('%H:%M:%S')}] [SERVICE] Initiating Solar-Pro Reasoning")
        
        # tqdm 대신 상세한 print 로깅
        if files:
            print(f"[{time.strftime('%H:%M:%S')}] [SERVICE] Found {len(files)} files to process")
            for f in files:
                print(f"  - Processing: {f.filename}")
                # 가상의 파일 읽기 및 임베딩 처리 과정
                _ = await f.read()
                print(f"  - Finished: {f.filename}")

        # Upstage API 호출
        print(f"[{time.strftime('%H:%M:%S')}] [LLM] Calling Upstage API...")
        # (실제 API 호출 로직 생략)
        return "에이전트 분석 결과입니다."