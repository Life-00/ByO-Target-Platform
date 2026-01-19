"""
Upstage LLM API 래퍼 서비스

- LLM 호출 (solar-1-mini-chat)
- 에러 처리 및 재시도
- Rate limiting 관리
- 토큰 사용량 추적
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """LLM 서비스 에러"""

    pass


class LLMRateLimitError(LLMServiceError):
    """Rate limit 초과"""

    pass


class LLMResponseError(LLMServiceError):
    """LLM 응답 에러"""

    pass


class LLMService:
    """Upstage LLM API 서비스 클래스"""

    def __init__(
        self,
        api_key: str = settings.upstage_api_key,
        model: str = settings.upstage_llm_model,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        request_timeout: int = 60,
    ):
        """
        Args:
            api_key: Upstage API 키
            model: 사용할 LLM 모델명
            max_retries: 재시도 횟수
            retry_delay: 재시도 대기 시간 (초)
            request_timeout: 요청 타임아웃 (초)
        """
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.request_timeout = request_timeout

        # Upstage는 OpenAI API 호환성 제공
        self.api_url = "https://api.upstage.ai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Rate limiting
        self.request_count = 0
        self.window_start = time.time()
        self.requests_per_minute = 60  # Upstage 무료 계정: 60 RPM

    async def _check_rate_limit(self):
        """Rate limit 확인"""
        current_time = time.time()
        elapsed = current_time - self.window_start

        # 1분마다 카운터 리셋
        if elapsed >= 60:
            self.request_count = 0
            self.window_start = current_time

        if self.request_count >= self.requests_per_minute:
            wait_time = 60 - elapsed
            raise LLMRateLimitError(f"Rate limit 초과. {wait_time:.1f}초 대기 필요")

        self.request_count += 1

    async def generate(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        system_prompt: Optional[str] = None,
    ) -> dict:
        """
        LLM 응답 생성

        Args:
            messages: 메시지 리스트 [{"role": "user", "content": "..."}, ...]
            temperature: 창의성 (0.0-2.0)
            max_tokens: 최대 토큰
            top_p: nucleus sampling
            system_prompt: 시스템 프롬프트 (messages 앞에 추가)

        Returns:
            {
                "content": "LLM 응답",
                "usage": {
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int
                },
                "finish_reason": "stop|length",
                "generated_at": datetime
            }
        """
        await self._check_rate_limit()

        # 시스템 프롬프트 추가
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        # 요청 페이로드
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }

        # 재시도 로직
        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.api_url,
                        json=payload,
                        headers=self.headers,
                        timeout=self.request_timeout,
                    )

                    if response.status_code == 429:
                        # Rate limit - 재시도
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limit 발생. {wait_time}초 대기 후 재시도 ({attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status_code != 200:
                        error_detail = response.text
                        raise LLMResponseError(
                            f"API 에러 (상태: {response.status_code}): {error_detail}"
                        )

                    data = response.json()

                    # 응답 파싱
                    if "choices" not in data or not data["choices"]:
                        raise LLMResponseError("응답에 choices가 없음")

                    choice = data["choices"][0]
                    content = choice.get("message", {}).get("content", "")
                    finish_reason = choice.get("finish_reason", "unknown")

                    usage = data.get("usage", {})

                    return {
                        "content": content,
                        "usage": {
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "completion_tokens": usage.get("completion_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                        },
                        "finish_reason": finish_reason,
                        "generated_at": datetime.now(ZoneInfo("Asia/Seoul")),
                    }

            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"타임아웃 발생. {wait_time}초 대기 후 재시도 ({attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                continue

            except httpx.RequestError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"요청 에러: {str(e)}. {wait_time}초 대기 후 재시도 ({attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                continue

            except LLMResponseError:
                raise

        # 모든 재시도 실패
        error_msg = f"LLM 요청 실패 ({self.max_retries}회 재시도 후)"
        if last_error:
            error_msg += f": {str(last_error)}"
        logger.error(error_msg)
        raise LLMServiceError(error_msg)

    async def generate_streaming(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        system_prompt: Optional[str] = None,
    ):
        """
        스트리밍 응답 생성

        Args:
            messages: 메시지 리스트
            temperature: 창의성
            max_tokens: 최대 토큰
            top_p: nucleus sampling
            system_prompt: 시스템 프롬프트

        Yields:
            스트리밍 토큰 또는 메타데이터
        """
        await self._check_rate_limit()

        # 시스템 프롬프트 추가
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        # 요청 페이로드
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.request_timeout,
                ) as response:
                    if response.status_code != 200:
                        error_detail = await response.atext()
                        raise LLMResponseError(
                            f"API 에러 (상태: {response.status_code}): {error_detail}"
                        )

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue

                        data_str = line[6:].strip()

                        if data_str == "[DONE]":
                            break

                        try:
                            data = eval(data_str)  # JSON 파싱 (eval 사용시 보안 주의)
                            if "choices" in data:
                                choice = data["choices"][0]
                                if "delta" in choice:
                                    delta = choice["delta"]
                                    if "content" in delta:
                                        yield {"type": "token", "content": delta["content"]}

                        except Exception as e:
                            logger.warning(f"스트리밍 데이터 파싱 에러: {str(e)}")
                            continue

        except httpx.TimeoutException as e:
            error_msg = f"스트리밍 타임아웃: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)

        except httpx.RequestError as e:
            error_msg = f"스트리밍 요청 에러: {str(e)}"
            logger.error(error_msg)
            raise LLMServiceError(error_msg)

    def count_tokens(self, text: str) -> int:
        """
        텍스트 토큰 수 추정

        Args:
            text: 텍스트

        Returns:
            추정 토큰 수
        """
        # 간단한 추정: 1 토큰 ≈ 4자
        return len(text) // 4 + 1

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        API 호출 비용 추정 (USD)

        Upstage Solar 1 Mini 기준:
        - 입력: $0.0004 / 1M 토큰
        - 출력: $0.0006 / 1M 토큰

        Args:
            prompt_tokens: 입력 토큰
            completion_tokens: 출력 토큰

        Returns:
            추정 비용 (USD)
        """
        input_cost = (prompt_tokens / 1_000_000) * 0.0004
        output_cost = (completion_tokens / 1_000_000) * 0.0006
        return input_cost + output_cost


# 싱글톤 인스턴스
_llm_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """LLM 서비스 인스턴스 반환 (싱글톤)"""
    global _llm_service_instance
    if _llm_service_instance is None:
        _llm_service_instance = LLMService()
    return _llm_service_instance
