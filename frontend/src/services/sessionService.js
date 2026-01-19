import apiClient from './apiClient';
import config from '../config/config';

/**
 * Session Service
 * 세션 관련 API 호출을 관리합니다.
 */

const sessionService = {
  /**
   * 세션 목록 조회
   * @param {number} limit - 조회할 세션 수 (기본값: 100)
   * @param {number} offset - 오프셋 (기본값: 0)
   */
  async getSessions(limit = 100, offset = 0) {
    try {
      const response = await apiClient.get(
        `${config.api.endpoints.sessions.list}?limit=${limit}&offset=${offset}`
      );
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  /**
   * 세션 생성
   * @param {Object} sessionData - 세션 데이터
   * @param {string} sessionData.title - 세션 제목
   * @param {string} sessionData.description - 세션 설명
   */
  async createSession(sessionData) {
    try {
      const response = await apiClient.post(config.api.endpoints.sessions.create, sessionData);
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  /**
   * 세션 상세 조회
   * @param {number} sessionId - 세션 ID
   */
  async getSession(sessionId) {
    try {
      const response = await apiClient.get(config.api.endpoints.sessions.get(sessionId));
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  /**
   * 세션 수정
   * @param {number} sessionId - 세션 ID
   * @param {Object} sessionData - 수정할 세션 데이터
   */
  async updateSession(sessionId, sessionData) {
    try {
      const response = await apiClient.put(
        config.api.endpoints.sessions.update(sessionId),
        sessionData
      );
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  /**
   * 세션 삭제
   * @param {number} sessionId - 세션 ID
   */
  async deleteSession(sessionId) {
    try {
      await apiClient.delete(config.api.endpoints.sessions.delete(sessionId));
      return true;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  /**
   * 세션 분석 목표 업데이트
   * @param {number} sessionId - 세션 ID
   * @param {string} analysisGoal - 분석 목표
   */
  async updateAnalysisGoal(sessionId, analysisGoal) {
    try {
      const response = await apiClient.put(
        `${config.api.endpoints.sessions.get(sessionId)}/goal`,
        { analysis_goal: analysisGoal }
      );
      return response;
    } catch (error) {
      throw this.handleError(error);
    }
  },

  /**
   * 에러 처리
   */
  handleError(error) {
    if (error.response) {
      const status = error.response.status;
      
      switch (status) {
        case 400:
          return new Error('잘못된 요청입니다.');
        case 401:
          return new Error('인증이 필요합니다. 다시 로그인해주세요.');
        case 403:
          return new Error('접근 권한이 없습니다.');
        case 404:
          return new Error('세션을 찾을 수 없습니다.');
        case 500:
          return new Error('서버 오류가 발생했습니다.');
        default:
          return new Error(error.response.data?.detail || '오류가 발생했습니다.');
      }
    }
    
    if (error.message === 'timeout') {
      return new Error('요청 시간이 초과되었습니다.');
    }
    
    return new Error('네트워크 오류가 발생했습니다.');
  },
};

export default sessionService;
