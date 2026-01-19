"""
Upstage Embedding API 래퍼 서비스

- 텍스트 임베딩 (upstage-embedding-passage)
- 배치 임베딩
- 캐싱 지원
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceError(Exception):
    """Embedding 서비스 에러"""

    pass


class EmbeddingRateLimitError(EmbeddingServiceError):
    """Rate limit 초과"""

    pass


class EmbeddingCache:
    """간단한 메모리 캐시 (TTL 지원)"""

    def __init__(self, ttl_seconds: int = 3600):
        """
        Args:
            ttl_seconds: 캐시 유지 시간 (기본 1시간)
        """
        self.cache: dict[str, dict] = {}
        self.ttl = ttl_seconds

    def _get_key(self, text: str) -> str:
        """텍스트 해시 생성"""
        return hashlib.md5(text.encode()).hexdigest()

    def get(self, text: str) -> Optional[list[float]]:
        """캐시에서 임베딩 조회"""
        key = self._get_key(text)
        if key not in self.cache:
            return None

        entry = self.cache[key]
        if datetime.now(ZoneInfo("Asia/Seoul")) > entry["expires"]:
            del self.cache[key]
            return None

        return entry["embedding"]

    def set(self, text: str, embedding: list[float]):
        """캐시에 임베딩 저장"""
        key = self._get_key(text)
        self.cache[key] = {
            "embedding": embedding,
            "expires": datetime.now(ZoneInfo("Asia/Seoul")) + timedelta(seconds=self.ttl),
        }

    def clear(self):
        """캐시 초기화"""
        self.cache.clear()


class EmbeddingService:
    """Upstage Embedding API 서비스 클래스"""

    def __init__(
        self,
        api_key: str = settings.upstage_api_key,
        model: str = settings.upstage_embedding_model,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        request_timeout: int = 60,
        enable_cache: bool = True,
        cache_ttl_seconds: int = 3600,
    ):
        """
        Args:
            api_key: Upstage API 키
            model: 임베딩 모델명
            max_retries: 재시도 횟수
            retry_delay: 재시도 대기 시간 (초)
            request_timeout: 요청 타임아웃 (초)
            enable_cache: 캐싱 활성화
            cache_ttl_seconds: 캐시 TTL (초)
        """
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.request_timeout = request_timeout

        # Upstage Embedding API
        self.api_url = "https://api.upstage.ai/v1/embeddings"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 캐시
        self.cache = EmbeddingCache(ttl_seconds=cache_ttl_seconds) if enable_cache else None

        # 임베딩 차원 (Upstage passage embedding: 4096차원)
        self.embedding_dim = 4096

    async def embed(
        self,
        text: str,
        use_cache: bool = True,
    ) -> dict:
        """
        단일 텍스트 임베딩

        Args:
            text: 텍스트
            use_cache: 캐시 사용 여부

        Returns:
            {
                "embedding": [float, ...],  # 1024차원
                "usage": {
                    "prompt_tokens": int,
                    "total_tokens": int
                },
                "embedded_at": datetime,
                "cached": bool
            }
        """
        # 캐시 확인
        if use_cache and self.cache:
            cached = self.cache.get(text)
            if cached is not None:
                return {
                    "embedding": cached,
                    "usage": {"prompt_tokens": 0, "total_tokens": 0},
                    "embedded_at": datetime.now(ZoneInfo("Asia/Seoul")),
                    "cached": True,
                }

        # API 호출
        payload = {"model": self.model, "input": text}

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
                        # Rate limit
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limit 발생. {wait_time}초 대기 후 재시도 ({attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    if response.status_code != 200:
                        error_detail = response.text
                        raise EmbeddingServiceError(
                            f"API 에러 (상태: {response.status_code}): {error_detail}"
                        )

                    data = response.json()

                    # 응답 파싱
                    if "data" not in data or not data["data"]:
                        raise EmbeddingServiceError("응답에 임베딩 데이터가 없음")

                    embedding = data["data"][0]["embedding"]
                    usage = data.get("usage", {})

                    # 캐시 저장
                    if self.cache:
                        self.cache.set(text, embedding)

                    return {
                        "embedding": embedding,
                        "usage": {
                            "prompt_tokens": usage.get("prompt_tokens", 0),
                            "total_tokens": usage.get("total_tokens", 0),
                        },
                        "embedded_at": datetime.now(ZoneInfo("Asia/Seoul")),
                        "cached": False,
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

        # 모든 재시도 실패
        error_msg = f"임베딩 요청 실패 ({self.max_retries}회 재시도 후)"
        if last_error:
            error_msg += f": {str(last_error)}"
        logger.error(error_msg)
        raise EmbeddingServiceError(error_msg)

    async def embed_batch(
        self,
        texts: list[str],
        use_cache: bool = True,
    ) -> dict:
        """
        배치 임베딩 (여러 텍스트 동시 처리)

        Args:
            texts: 텍스트 리스트 (권장: 100개 이하)
            use_cache: 캐시 사용 여부

        Returns:
            {
                "embeddings": [[float, ...], ...],  # 각 1024차원
                "usage": {
                    "prompt_tokens": int,
                    "total_tokens": int
                },
                "embedded_at": datetime,
                "cached_count": int,
                "api_count": int
            }
        """
        embeddings = []
        total_usage = {"prompt_tokens": 0, "total_tokens": 0}
        cached_count = 0
        api_count = 0

        # 캐시 확인
        texts_to_embed = []
        cache_indices = {}

        if use_cache and self.cache:
            for i, text in enumerate(texts):
                cached = self.cache.get(text)
                if cached is not None:
                    embeddings.append(cached)
                    cached_count += 1
                else:
                    cache_indices[len(texts_to_embed)] = i
                    texts_to_embed.append(text)
        else:
            texts_to_embed = texts

        # API 호출 (배치)
        if texts_to_embed:
            payload = {"model": self.model, "input": texts_to_embed}

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
                            # Rate limit
                            wait_time = self.retry_delay * (2 ** attempt)
                            logger.warning(
                                f"배치 Rate limit. {wait_time}초 대기 후 재시도 ({attempt + 1}/{self.max_retries})"
                            )
                            await asyncio.sleep(wait_time)
                            continue

                        if response.status_code != 200:
                            error_detail = response.text
                            raise EmbeddingServiceError(
                                f"API 에러 (상태: {response.status_code}): {error_detail}"
                            )

                        data = response.json()

                        if "data" not in data:
                            raise EmbeddingServiceError("응답에 임베딩 데이터가 없음")

                        # 응답 파싱
                        api_embeddings = []
                        for item in data["data"]:
                            api_embeddings.append(item["embedding"])
                            if use_cache and self.cache:
                                self.cache.set(texts_to_embed[item["index"]], item["embedding"])

                        # 원래 순서대로 정렬
                        sorted_embeddings = [None] * len(texts_to_embed)
                        for api_idx, item in enumerate(data["data"]):
                            sorted_embeddings[item["index"]] = item["embedding"]

                        # embeddings 배열에 추가
                        for api_idx, text_idx in cache_indices.items():
                            embeddings.insert(text_idx, sorted_embeddings[api_idx])

                        usage = data.get("usage", {})
                        total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                        total_usage["total_tokens"] += usage.get("total_tokens", 0)
                        api_count = len(texts_to_embed)

                        break

                except httpx.TimeoutException as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"배치 타임아웃. {wait_time}초 대기 후 재시도")
                        await asyncio.sleep(wait_time)
                    continue

                except httpx.RequestError as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"배치 요청 에러: {str(e)}. {wait_time}초 대기 후 재시도")
                        await asyncio.sleep(wait_time)
                    continue

            if last_error:
                error_msg = f"배치 임베딩 실패: {str(last_error)}"
                logger.error(error_msg)
                raise EmbeddingServiceError(error_msg)

        return {
            "embeddings": embeddings,
            "usage": total_usage,
            "embedded_at": datetime.now(ZoneInfo("Asia/Seoul")),
            "cached_count": cached_count,
            "api_count": api_count,
        }

    async def add_documents(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict]
    ):
        """
        Add documents to ChromaDB
        
        Args:
            ids: List of unique IDs for each document
            embeddings: List of embedding vectors
            documents: List of text content
            metadatas: List of metadata dicts
        """
        try:
            # Lazy import to avoid numpy compatibility issues at module load time
            import chromadb
            
            # Connect to ChromaDB with error handling
            try:
                client = chromadb.HttpClient(
                    host=settings.chromadb_host,
                    port=settings.chromadb_port
                )
                
                # Get or create collection
                collection = client.get_or_create_collection(
                    name="document_embeddings",
                    metadata={"description": "PDF document embeddings"}
                )
                
                # Add documents
                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas
                )
                
                logger.info(f"[EmbeddingService] Added {len(ids)} documents to ChromaDB")
                
            except AttributeError as numpy_err:
                if "np.float_" in str(numpy_err):
                    logger.warning(f"[EmbeddingService] NumPy 2.0 compatibility issue with ChromaDB. Embeddings stored in PostgreSQL but not in ChromaDB: {str(numpy_err)}")
                    # Don't raise - PostgreSQL still has the data
                    return
                raise
            
        except EmbeddingServiceError:
            raise
        except Exception as e:
            logger.error(f"[EmbeddingService] ChromaDB add failed: {str(e)}")
            # Don't raise - allow the process to continue with PostgreSQL data
            logger.warning(f"[EmbeddingService] Continuing without ChromaDB storage. Data is in PostgreSQL.")

    def clear_cache(self):
        """캐시 초기화"""
        if self.cache:
            self.cache.clear()


# 싱글톤 인스턴스
_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Embedding 서비스 인스턴스 반환 (싱글톤)"""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance
