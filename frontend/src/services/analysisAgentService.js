/**
 * Analysis Agent Service
 * RAG 기반 문서 분석 및 근거 제시
 */

import apiClient from './apiClient';
import authService from './authService';
import config from '../config/config';

const analysisAgentService = {
  /**
   * 문서 분석 요청
   * @param {number} sessionId - 세션 ID
   * @param {string} content - 사용자 질문
   * @param {string} analysisGoal - 분석 목표
   * @param {Array} selectedDocuments - 분석 대상 문서들
   * @param {number} topK - 검색할 청크 개수
   * @param {number} minRelevanceScore - 최소 관련성 점수
   * @returns {Promise<Object>} - 분석 결과 (답변 + 근거)
   */
  async analyze(sessionId, content, analysisGoal = null, selectedDocuments = [], topK = 5, minRelevanceScore = 0.5) {
    try {
      const endpoint = config.api.endpoints.agents.analysis;
      const payload = {
        session_id: sessionId,
        user_id: authService.getUserId(),
        content: content,
        selected_documents: selectedDocuments,
        top_k: topK,
        min_relevance_score: minRelevanceScore,
      };

      if (analysisGoal) {
        payload.analysis_goal = analysisGoal;
      }

      console.log('[AnalysisAgentService] Analyzing documents:', payload);
      const response = await apiClient.post(endpoint, payload);
      console.log('[AnalysisAgentService] Analysis results:', response);
      return response;
    } catch (error) {
      console.error('[AnalysisAgentService] Analysis error:', error);
      throw error;
    }
  },
};

export default analysisAgentService;
