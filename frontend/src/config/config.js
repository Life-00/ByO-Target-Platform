/**
 * Frontend Configuration
 * 중앙화된 설정 관리
 * 환경 변수에서 설정을 읽고 기본값을 제공합니다.
 */

const config = {
  // API Configuration
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001',
    version: import.meta.env.VITE_API_VERSION || 'v1',
    
    get apiUrl() {
      return `${this.baseUrl}/api/${this.version}`;
    },

    // Endpoint URLs
    endpoints: {
      auth: {
        register: '/auth/register',
        login: '/auth/login',
        refresh: '/auth/refresh',
        logout: '/auth/logout',
      },
      sessions: {
        list: '/sessions',
        create: '/sessions',
        get: (id) => `/sessions/${id}`,
        update: (id) => `/sessions/${id}`,
        delete: (id) => `/sessions/${id}`,
      },
      documents: {
        list: '/documents',
        upload: '/documents/upload',
        get: (id) => `/documents/${id}`,
        delete: (id) => `/documents/${id}`,
        download: (id) => `/documents/${id}/download`,
        session: '/documents/session',
      },
      chat: {
        message: '/agents/general/message',
        history: '/agents/general/history',
        deleteMessage: (id) => `/agents/general/${id}`,
        clearSession: (sessionId) => `/agents/general/session/${sessionId}`,
      },
      agents: {
        embedding: '/agents/embedding',
        search: '/agents/search',
        analysis: '/agents/analysis',
        general: {
          message: '/agents/general/message',
          history: '/agents/general/history',
          health: '/agents/general/health',
        },
      },
    },
  },

  // App Configuration
  app: {
    name: import.meta.env.VITE_APP_NAME || 'TVA',
    description: import.meta.env.VITE_APP_DESCRIPTION || 'Target Validation Assistant',
  },

  // Feature Flags
  features: {
    debug: import.meta.env.VITE_ENABLE_DEBUG === 'true',
  },

  // Session Configuration
  session: {
    timeoutMinutes: parseInt(import.meta.env.VITE_SESSION_TIMEOUT_MINUTES || '30'),
    tokenRefreshBufferMinutes: parseInt(import.meta.env.VITE_TOKEN_REFRESH_BUFFER_MINUTES || '5'),
    storageKeys: {
      accessToken: 'access_token',
      refreshToken: 'refresh_token',
      user: 'user',
    },
  },

  // HTTP Configuration
  http: {
    defaultHeaders: {
      'Content-Type': 'application/json',
    },
    timeout: 120000, // 120 seconds (for search agent queries)
  },
};

export default config;
