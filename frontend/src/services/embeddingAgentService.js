/**
 * Embedding Agent Service
 * PDF 문서 분석 및 임베딩 관련 API 호출
 */

import apiClient from './apiClient';
import config from '../config/config';

const embeddingAgentService = {
  /**
   * PDF 문서 분석 (EmbeddingAgent 실행)
   * 텍스트 추출, 청킹, 임베딩, 요약 생성 포함
   * 
   * @param {number} documentId - 문서 ID
   * @param {string} sessionId - 세션 ID
   * @param {number} chunkSize - 청크 크기 (기본값: 500)
   * @returns {Promise<Object>} - 분석 결과
   *   {
   *     status: 'success',
   *     document_id: number,
   *     chunks_created: number,
   *     embeddings_generated: number,
   *     summary: string,
   *     metadata: {
   *       page_count: number,
   *       keywords: string[],
   *       sections: string[]
   *     }
   *   }
   */
  async analyzeDocument(documentId, sessionId, chunkSize = 500) {
    try {
      const endpoint = config.api.endpoints.agents.embedding;
      const payload = {
        document_id: documentId,
        session_id: sessionId,
        chunk_size: chunkSize,
      };

      console.log('[EmbeddingAgentService] Analyzing document:', payload);
      const response = await apiClient.post(endpoint, payload);
      console.log('[EmbeddingAgentService] Analysis complete:', {
        documentId: response.document_id,
        chunks: response.chunks_created,
        embeddings: response.embeddings_generated,
      });
      return response;
    } catch (error) {
      console.error('Document analysis error:', error);
      throw error;
    }
  },

  /**
   * 문서 임베딩 상태 확인
   * @param {number} documentId - 문서 ID
   * @returns {Promise<Object>} - 임베딩 상태
   */
  async getEmbeddingStatus(documentId) {
    try {
      const endpoint = `${config.api.endpoints.agents.embedding}/${documentId}/status`;
      console.log('[EmbeddingAgentService] Checking embedding status:', documentId);
      return await apiClient.get(endpoint);
    } catch (error) {
      console.error('Get embedding status error:', error);
      throw error;
    }
  },

  /**
   * 문서 청크 조회
   * @param {number} documentId - 문서 ID
   * @param {number} limit - 조회 개수
   * @param {number} offset - 시작 위치
   * @returns {Promise<Object>} - 청크 목록
   */
  async getDocumentChunks(documentId, limit = 50, offset = 0) {
    try {
      const endpoint = `${config.api.endpoints.agents.embedding}/${documentId}/chunks?limit=${limit}&offset=${offset}`;
      console.log('[EmbeddingAgentService] Fetching document chunks:', documentId);
      return await apiClient.get(endpoint);
    } catch (error) {
      console.error('Get chunks error:', error);
      throw error;
    }
  },

  /**
   * 문서 요약 조회
   * @param {number} documentId - 문서 ID
   * @returns {Promise<Object>} - 문서 요약
   */
  async getDocumentSummary(documentId) {
    try {
      const endpoint = `${config.api.endpoints.agents.embedding}/${documentId}/summary`;
      console.log('[EmbeddingAgentService] Fetching document summary:', documentId);
      return await apiClient.get(endpoint);
    } catch (error) {
      console.error('Get summary error:', error);
      throw error;
    }
  },

  /**
   * 문서 재분석 (기존 임베딩 재생성)
   * @param {number} documentId - 문서 ID
   * @param {number} chunkSize - 새로운 청크 크기
   * @returns {Promise<Object>} - 재분석 결과
   */
  async reanalyzeDocument(documentId, chunkSize = 500) {
    try {
      const endpoint = `${config.api.endpoints.agents.embedding}/${documentId}/reanalyze`;
      const payload = {
        chunk_size: chunkSize,
      };

      console.log('[EmbeddingAgentService] Reanalyzing document:', documentId);
      const response = await apiClient.post(endpoint, payload);
      console.log('[EmbeddingAgentService] Reanalysis complete');
      return response;
    } catch (error) {
      console.error('Document reanalysis error:', error);
      throw error;
    }
  },
};

export default embeddingAgentService;
