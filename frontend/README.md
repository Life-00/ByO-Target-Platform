📂 1. 파일 구조
React + Vite

```
frontend/
├── public/                 # 정적 자산 (로고 등)
│   └── TVA.png             # 서비스 로고 이미지
├── src/
│   ├── api/                # API 통신 관련 설정
│   │   ├── client.js       # Axios 인스턴스 기본 설정
│   │   └── index.js        # 토큰 인터셉터 및 중앙 API 클라이언트
│   ├── assets/             # 컴포넌트 내부 사용 이미지 자산
│   ├── components/         # 기능별 UI 컴포넌트
│   │   ├── Auth/           # 인증(로그인/회원가입) 섹션
│   │   │   ├── AuthContainer.css
│   │   │   └── AuthContainer.jsx
│   │   └── Dashboard/      # 메인 분석 대화창 섹션
│   │       ├── Dashboard.css
│   │       └── Dashboard.jsx
│   ├── App.css             # 글로벌 레이아웃 및 공통 스타일
│   ├── App.jsx             # 메인 라우팅 및 인증 분기 로직
│   ├── index.css           # CSS 테마 변수 정의
│   └── main.jsx            # React 엔트리 포인트
├── .env                    # 백엔드 주소 환경 변수 설정
├── Dockerfile              # 프론트엔드 컨테이너 빌드 설정
├── index.html              # 메인 HTML 템플릿
├── package.json            # 의존성 및 실행 스크립트 정의
└── vite.config.js          # Vite 번들러 및 프록시 설정
```

⚙️ 2. 주요 설정 방법

1. API 통신 설정 (src/api/index.js)

   - Base URL: 환경 변수(VITE_API_BASE_URL)를 통해 백엔드 주소를 동적으로 관리합니다.
   - JWT 인터셉터: localStorage에서 token을 읽어 모든 요청 헤더에 Authorization: Bearer <token>을 자동으로 주입합니다.

2. 테마 변수 (src/index.css)

   - bio-primary: 서비스의 핵심 색상 (다크 틸).
   - bio-secondary: 사이드바 및 배경색.

🚀 3. 설치 및 실행 방법

1. 의존성 패키지 설치

   ```
   npm install
   ```

2. 환경 변수 설정
   프로젝트 루트에 .env 파일을 만들고 백엔드 API 주소를 입력합니다.

   ```
   VITE_API_BASE_URL=""
   ```

3. 개발 서버 실행
   ```
   npm run dev
   ```
