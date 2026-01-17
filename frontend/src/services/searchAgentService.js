/**
 * Search Agent Service
 * arXiv 논문 검색 및 다운로드
 */

import apiClient from './apiClient';
import authService from './authService';
import config from '../config/config';

const searchAgentService = {
  /**
   * arXiv 논문 검색 및 다운로드
   * @param {number} sessionId - 세션 ID
   * @param {string} content - 검색 질문
   * @param {string} analysisGoal - 분석 목표
   * @param {Array} selectedDocuments - 이미 다운로드된 문서 목록 (중복 방지)
   * @param {number} minRelevanceScore - 최소 관련성 점수
   * @returns {Promise<Object>} - 검색 결과 및 다운로드된 논문들
   */
  async search(sessionId, content, analysisGoal = null, selectedDocuments = null, minRelevanceScore = 0.7) {
    try {
      const endpoint = config.api.endpoints.agents.search;
      const payload = {
        session_id: sessionId,
        user_id: authService.getUserId(),
        content: content,
        min_relevance_score: minRelevanceScore,
      };

      if (analysisGoal) {
        payload.analysis_goal = analysisGoal;
      }

      if (selectedDocuments && selectedDocuments.length > 0) {
        payload.selected_documents = selectedDocuments;
      }

      console.log('[SearchAgentService] Searching papers:', payload);
      const response = await apiClient.post(endpoint, payload);
      console.log('[SearchAgentService] Search results:', response);
      return response;
    } catch (error) {
      console.error('[SearchAgentService] Search error:', error);
      throw error;
    }
  },
};

export default searchAgentService;
