# 🔌 TVA Frontend - API 확인 문서

**날짜**: 2026-01-17  
**Backend**: http://localhost:8001

---

## ⚙️ API Base URL

```javascript
const API_BASE = 'http://localhost:8001/api/v1';
```

---

## 🔐 인증 (Auth)

### 회원가입
```
POST /api/v1/auth/register
```

**요청 본문:**
```json
{
  "username": "tva",
  "email": "tva@tva.com",
  "password": "tva12345",
  "full_name": "TVA Team"  // Optional (선택사항)
}
```

**응답:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "tva",
    "email": "tva@tva.com",
    "full_name": "TVA Team",
    "is_active": true,
    "created_at": "2026-01-17T13:00:00+09:00"
  }
}
```

**테스트 계정:**
- Email: `tva@tva.com`
- Password: `tva12345`
- Full Name: `TVA Team` (Optional)

---

### 로그인
```
POST /api/v1/auth/login
```

**요청 본문:**
```json
{
  "email": "tva@tva.com",
  "password": "tva12345"
}
```

**응답:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "tva",
    "email": "tva@tva.com",
    "full_name": "TVA Team",
    "is_active": true
  }
}
```

---

### 토큰 갱신
```
POST /api/v1/auth/refresh
```

**요청 본문:**
```json
{
  "refresh_token": "eyJ..."
}
```

**응답:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

### 비밀번호 변경
```
POST /api/v1/auth/change-password
Authorization: Bearer {access_token}
```

**요청 본문:**
```json
{
  "old_password": "tva12345",
  "new_password": "newtva12345"
}
```

---

## 📁 세션 (Sessions)

### 세션 목록 조회
```
GET /api/v1/sessions
Authorization: Bearer {access_token}
```

**쿼리 파라미터:**
- `limit`: 1-100 (기본값: 10)
- `offset`: 0부터 시작 (기본값: 0)

**응답:**
```json
{
  "total": 5,
  "limit": 10,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "title": "CRISPR Research",
      "description": "Gene editing studies",
      "created_at": "2026-01-17T10:00:00+09:00",
      "updated_at": "2026-01-17T10:00:00+09:00"
    }
  ]
}
```

---

### 세션 생성
```
POST /api/v1/sessions
Authorization: Bearer {access_token}
```

**요청 본문:**
```json
{
  "title": "CRISPR Research",
  "description": "Gene editing studies"
}
```

**응답:**
```json
{
  "id": 1,
  "title": "CRISPR Research",
  "description": "Gene editing studies",
  "created_at": "2026-01-17T10:00:00+09:00",
  "updated_at": "2026-01-17T10:00:00+09:00"
}
```

---

### 세션 상세 조회
```
GET /api/v1/sessions/{session_id}
Authorization: Bearer {access_token}
```

---

### 세션 수정
```
PUT /api/v1/sessions/{session_id}
Authorization: Bearer {access_token}
```

**요청 본문:**
```json
{
  "title": "Updated Title",
  "description": "Updated description"
}
```

---

### 세션 삭제
```
DELETE /api/v1/sessions/{session_id}
Authorization: Bearer {access_token}
```

---

## 📄 문서 (Documents)

### 문서 목록 조회
```
GET /api/v1/documents
Authorization: Bearer {access_token}
```

**쿼리 파라미터:**
- `limit`: 1-500 (기본값: 10)
- `offset`: 0부터 시작 (기본값: 0)

**응답:**
```json
{
  "total": 3,
  "limit": 10,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "filename": "paper.pdf",
      "title": "CRISPR Applications",
      "page_count": 25,
      "source": "arxiv",
      "external_id": "2401.12345",
      "keywords": ["CRISPR", "gene-editing"],
      "sections": ["Introduction", "Methods", "Results"],
      "relevance_score": 0.92,
      "created_at": "2026-01-17T10:00:00+09:00"
    }
  ]
}
```

---

### PDF 업로드
```
POST /api/v1/documents/upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Form 데이터:**
- `file`: PDF 파일 (필수)
- `title`: 문서 제목 (선택사항)
- `description`: 문서 설명 (선택사항)

**제약사항:**
- 최대 파일 크기: 50MB
- PDF 파일만 가능

**응답:**
```json
{
  "id": 1,
  "filename": "paper.pdf",
  "title": "Document Title",
  "page_count": 25,
  "file_size": 2048576,
  "created_at": "2026-01-17T10:00:00+09:00"
}
```

---

### 문서 상세 조회
```
GET /api/v1/documents/{doc_id}
Authorization: Bearer {access_token}
```

---

### 문서 삭제
```
DELETE /api/v1/documents/{doc_id}
Authorization: Bearer {access_token}
```

---

## 💬 채팅 (Chat)

### 메시지 전송
```
POST /api/v1/chat/message
Authorization: Bearer {access_token}
```

**요청 본문:**
```json
{
  "session_id": 1,
  "content": "What is CRISPR?",
  "citations_enabled": true
}
```

**응답:**
```json
{
  "id": 1,
  "session_id": 1,
  "role": "assistant",
  "content": "CRISPR is a gene editing technology...",
  "citations": [
    {
      "document_id": 1,
      "page": 5,
      "text": "CRISPR-Cas9..."
    }
  ],
  "created_at": "2026-01-17T10:00:00+09:00"
}
```

---

### 채팅 이력 조회
```
GET /api/v1/chat/history
Authorization: Bearer {access_token}
```

**쿼리 파라미터:**
- `session_id`: 세션 ID (필수)
- `limit`: 1-100 (기본값: 50)
- `offset`: 0부터 시작 (기본값: 0)

---

### 메시지 삭제
```
DELETE /api/v1/chat/{message_id}
Authorization: Bearer {access_token}
```

---

### 세션 초기화
```
DELETE /api/v1/chat/session/{session_id}/clear
Authorization: Bearer {access_token}
```

---

## 🤖 논문 검색 (Agents - Search)

### 논문 검색
```
POST /api/v1/agents/search
Authorization: Bearer {access_token}
```

**요청 본문:**
```json
{
  "query": "CRISPR gene editing",
  "source": "both",
  "max_results_to_fetch": 50,
  "min_relevant_papers": 10,
  "auto_determine_count": true,
  "download_pdf": true,
  "extract_metadata": true
}
```

**파라미터 설명:**
- `query`: 검색 쿼리 (필수)
- `source`: "arxiv" | "pubmed" | "both" (기본값: "both")
- `max_results_to_fetch`: 최대 가져올 논문 수 (기본값: 50)
- `min_relevant_papers`: 최소 관련성 논문 수 (기본값: 10)
- `auto_determine_count`: 자동으로 개수 결정 (기본값: true)
- `download_pdf`: PDF 다운로드 (기본값: true)
- `extract_metadata`: 메타데이터 추출 (기본값: true)

**응답:**
```json
{
  "query": "CRISPR gene editing",
  "source": "both",
  "total_found": 12,
  "papers": [
    {
      "id": 1,
      "paper_id": "2401.12345",
      "source": "arxiv",
      "title": "CRISPR-Cas9 mechanisms",
      "authors": ["John Doe", "Jane Smith"],
      "published_date": "2024-01-15",
      "abstract": "This paper reviews...",
      "relevance_score": 0.92,
      "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
      "pdf_path": "/uploads/user1/papers/2401_12345.pdf",
      "page_count": 18,
      "keywords": ["CRISPR", "gene-editing"],
      "sections": ["Introduction", "Methods", "Results"],
      "extracted_abstract": "Abstract text..."
    }
  ],
  "downloaded_count": 12,
  "search_time_seconds": 14.7,
  "from_cache": false
}
```

---

## 🏥 헬스 체크

### API 상태 확인
```
GET /health
```

**응답:**
```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0"
}
```

---

## 📚 API 문서 (Swagger UI)

**Swagger UI**: http://localhost:8001/docs  
**ReDoc**: http://localhost:8001/redoc

---

## 🔒 인증 방식

모든 보호된 엔드포인트는 **Authorization** 헤더가 필요합니다:

```
Authorization: Bearer {access_token}
```

### JavaScript 예시:
```javascript
const token = localStorage.getItem('access_token');

const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${token}`
};

const response = await fetch('http://localhost:8001/api/v1/agents/search', {
  method: 'POST',
  headers: headers,
  body: JSON.stringify({
    query: 'CRISPR',
    source: 'both'
  })
});
```

---

## ⚠️ 에러 응답

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

**해결**: Access token이 없거나 만료됨. 새로 로그인하거나 토큰 갱신.

### 403 Forbidden
```json
{
  "detail": "Not authorized"
}
```

**해결**: 권한 부족. 올바른 토큰으로 재시도.

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters"
    }
  ]
}
```

**해결**: 요청 데이터 형식 확인. Password는 최소 8자.

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

**해결**: Backend 로그 확인. 심각한 에러이므로 개발자에게 보고.

---

## 💾 로컬 스토리지 사용

```javascript
// 로그인 후
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);
localStorage.setItem('user', JSON.stringify(response.user));

// 로그아웃 시
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
localStorage.removeItem('user');

// 토큰 사용
const token = localStorage.getItem('access_token');
```

---

## 🧪 테스트 케이스

### 1. 회원가입 → 로그인 → 논문 검색
```bash
# 1. 회원가입
curl -X POST http://localhost:8001/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"tva","email":"tva@tva.com","password":"tva12345","full_name":"TVA Team"}'

# 2. 로그인
TOKEN=$(curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"tva@tva.com","password":"tva12345"}' | jq -r '.access_token')

# 3. 논문 검색
curl -X POST http://localhost:8001/api/v1/agents/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"CRISPR","source":"both","download_pdf":true}'
```

---

**마지막 업데이트**: 2026-01-17  
**상태**: ✅ Backend 모든 API 준비 완료
