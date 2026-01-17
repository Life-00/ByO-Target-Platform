/**
 * API Client Service
 * 모든 API 요청을 관리하는 중앙화된 서비스
 * 환경 설정, 에러 처리, 토큰 관리를 담당합니다.
 */

import config from '../config/config';

class APIClient {
  constructor() {
    this.baseUrl = config.api.apiUrl;
    this.timeout = config.http.timeout;
  }

  /**
   * 요청에 인증 토큰 추가
   */
  getAuthHeaders() {
    const accessToken = localStorage.getItem(config.session.storageKeys.accessToken);
    const headers = {
      ...config.http.defaultHeaders,
    };

    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    return headers;
  }

  /**
   * 기본 fetch 요청 메서드
   */
  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
    
    const fetchOptions = {
      ...options,
      headers: {
        ...this.getAuthHeaders(),
        ...(options.headers || {}),
      },
    };

    try {
      const response = await Promise.race([
        fetch(url, fetchOptions),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Request timeout')), this.timeout)
        ),
      ]);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw {
          status: response.status,
          message: errorData.detail || `HTTP Error: ${response.status}`,
          data: errorData,
        };
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error [${options.method || 'GET'} ${url}]:`, error);
      throw error;
    }
  }

  /**
   * GET 요청
   */
  get(endpoint, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'GET',
    });
  }

  /**
   * POST 요청
   */
  post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * PUT 요청
   */
  put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  /**
   * DELETE 요청
   */
  delete(endpoint, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'DELETE',
    });
  }

  /**
   * PATCH 요청
   */
  patch(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }
}

// 싱글톤 인스턴스
const apiClient = new APIClient();

export default apiClient;
