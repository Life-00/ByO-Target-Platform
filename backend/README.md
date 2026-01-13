📂 1. 파일 구조

```
backend/
├── app/
│   ├── api/v1/             # API 엔드포인트 정의 레이어
│   │   ├── auth.py         # 로그인, 회원가입 관련 API 입구
│   │   └── chat.py         # 채팅 세션 및 LLM 질의응답 API 입구
│   ├── core/               # 앱 전체의 시스템 설정 레이어
│   │   ├── config.py       # [중요] Pydantic Settings 기반 환경 변수 검증 및 로드
│   │   └── database.py     # SQLAlchemy DB 엔진 및 세션 팩토리 설정
│   ├── models/             # 데이터베이스 테이블 스키마 정의 (DB 구조)
│   │   ├── user.py         # 사용자 정보 테이블 정의
│   │   └── user_db.py      # 사용자별 분석 히스토리 등 데이터 매핑
│   ├── service/            # 비즈니스 로직 처리 레이어 (핵심 엔진)
│   │   ├── auth_service.py # JWT 토큰 생성 및 비밀번호 암호화 로직
│   │   ├── rag_service.py  # 문서 업로드, 벡터화 및 검색(ChromaDB) 엔진
│   │   └── solar_service.py# Upstage Solar LLM 호출 및 에이전트 추론 로직
│   └── agents/             # 복합적인 에이전트 워크플로우 정의
├── main.py                 # FastAPI 애플리케이션 진입점 (CORS 및 미들웨어 설정)
├── Dockerfile              # uv 기반의 고성능 도커 이미지 빌드 설정
├── pyproject.toml          # uv/python 의존성 및 프로젝트 메타데이터
└── uv.lock                 # 의존성 버전 잠금 파일
```
