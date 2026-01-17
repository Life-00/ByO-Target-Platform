/**
 * Authentication Service
 * 회원가입, 로그인, 토큰 관리를 담당합니다.
 */

import apiClient from './apiClient';
import config from '../config/config';

class AuthService {
  /**
   * 회원가입
   */
  async register(userData) {
    try {
      const response = await apiClient.post(config.api.endpoints.auth.register, {
        username: userData.username,
        email: userData.email,
        password: userData.password,
        full_name: userData.fullName || undefined,
      });

      // 토큰 저장
      this.setTokens(response.access_token, response.refresh_token);
      
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * 로그인
   */
  async login(email, password) {
    try {
      const response = await apiClient.post(config.api.endpoints.auth.login, {
        email,
        password,
      });

      // 토큰 저장
      this.setTokens(response.access_token, response.refresh_token);
      
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  /**
   * 토큰 리프레시
   */
  async refreshToken() {
    try {
      const refreshToken = localStorage.getItem(config.session.storageKeys.refreshToken);
      
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await apiClient.post(config.api.endpoints.auth.refresh, {
        refresh_token: refreshToken,
      });

      this.setTokens(response.access_token, response.refresh_token);
      
      return response;
    } catch (error) {
      // 리프레시 실패 시 로그아웃
      this.logout();
      throw this.handleError(error);
    }
  }

  /**
   * 로그아웃 (서버 API 호출)
   */
  async logoutAsync() {
    try {
      const endpoint = config.api.endpoints.auth.logout;
      const accessToken = localStorage.getItem(config.session.storageKeys.accessToken);
      
      // 토큰이 있으면 서버에 로그아웃 요청
      if (accessToken) {
        try {
          await apiClient.post(endpoint);
        } catch (error) {
          console.warn('Logout API call failed, clearing local tokens:', error);
        }
      }
      
      // 로컬 스토리지에서 토큰 제거
      localStorage.removeItem(config.session.storageKeys.accessToken);
      localStorage.removeItem(config.session.storageKeys.refreshToken);
      localStorage.removeItem(config.session.storageKeys.user);
    } catch (error) {
      console.error('Logout error:', error);
      // 에러가 발생해도 로컬 토큰은 제거
      localStorage.removeItem(config.session.storageKeys.accessToken);
      localStorage.removeItem(config.session.storageKeys.refreshToken);
      localStorage.removeItem(config.session.storageKeys.user);
      throw error;
    }
  }

  /**
   * 로그아웃 (동기)
   */
  logout() {
    localStorage.removeItem(config.session.storageKeys.accessToken);
    localStorage.removeItem(config.session.storageKeys.refreshToken);
    localStorage.removeItem(config.session.storageKeys.user);
  }

  /**
   * 토큰 저장
   */
  setTokens(accessToken, refreshToken) {
    localStorage.setItem(config.session.storageKeys.accessToken, accessToken);
    localStorage.setItem(config.session.storageKeys.refreshToken, refreshToken);
  }

  /**
   * 액세스 토큰 가져오기
   */
  getAccessToken() {
    return localStorage.getItem(config.session.storageKeys.accessToken);
  }

  /**
   * JWT 토큰에서 user_id 추출
   */
  getUserId() {
    const token = this.getAccessToken();
    if (!token) return null;
    
    try {
      // JWT는 header.payload.signature 형식
      const payload = token.split('.')[1];
      const decoded = JSON.parse(atob(payload));
      return decoded.user_id || decoded.sub; // user_id 또는 sub 필드
    } catch (error) {
      console.error('Failed to decode token:', error);
      return null;
    }
  }

  /**
   * 토큰 유효 여부 확인
   */
  isAuthenticated() {
    return !!this.getAccessToken();
  }

  /**
   * 에러 처리
   */
  handleError(error) {
    if (error.status === 400) {
      // 입력 검증 오류
      return new Error(error.data.detail || '입력값을 확인해주세요.');
    }
    if (error.status === 401) {
      // 인증 오류
      this.logout();
      return new Error('인증이 만료되었습니다. 다시 로그인해주세요.');
    }
    if (error.status === 409) {
      // 충돌 (중복)
      return new Error(error.data.detail || '이미 등록된 정보입니다.');
    }
    if (error.message === 'Request timeout') {
      return new Error('요청 시간이 초과되었습니다.');
    }
    return new Error(error.message || '오류가 발생했습니다.');
  }
}

// 싱글톤 인스턴스
const authService = new AuthService();

export default authService;
