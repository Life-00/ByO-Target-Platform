/**
 * General Chat Service
 * 일반 LLM 채팅 서비스
 */

import apiClient from './apiClient';
import config from '../config/config';

const generalChatService = {
  /**
   * 메시지 전송
   * @param {number} sessionId - 세션 ID
   * @param {string} content - 메시지 내용
   * @param {string} systemPrompt - 시스템 프롬프트 (선택)
   * @param {number} temperature - Temperature (선택)
   * @param {number} maxTokens - Max tokens (선택)
   * @param {Array} selectedDocuments - 선택된 문서들 (선택)
   * @param {string} analysisGoal - 분석 목표 (선택)
   * @returns {Promise<Object>} - LLM 응답
   */
  async sendMessage(
    sessionId,
    content,
    systemPrompt = null,
    temperature = 0.7,
    maxTokens = 2048,
    selectedDocuments = null,
    analysisGoal = null
  ) {
    try {
      const endpoint = config.api.endpoints.chat.message;
      const payload = {
        session_id: sessionId,
        content: content,
        temperature: temperature,
        max_tokens: maxTokens,
      };

      if (systemPrompt) {
        payload.system_prompt = systemPrompt;
      }

      if (selectedDocuments && selectedDocuments.length > 0) {
        payload.selected_documents = selectedDocuments.map(doc => ({
          id: doc.id,
          title: doc.title,
          summary: doc.summary || null,
        }));
      }

      if (analysisGoal) {
        payload.analysis_goal = analysisGoal;
      }

      console.log('[GeneralChatService] Sending message:', payload);
      const response = await apiClient.post(endpoint, payload);
      console.log('[GeneralChatService] Response received');
      return response;
    } catch (error) {
      console.error('Send message error:', error);
      throw error;
    }
  },

  /**
   * 채팅 히스토리 조회
   * @param {number} sessionId - 세션 ID
   * @param {number} limit - 가져올 개수
   * @param {number} offset - 시작 위치
   * @returns {Promise<Object>} - 채팅 히스토리
   */
  async getHistory(sessionId, limit = 50, offset = 0) {
    try {
      const endpoint = `${config.api.endpoints.chat.history}?session_id=${sessionId}&limit=${limit}&offset=${offset}`;
      console.log('[GeneralChatService] Fetching history:', endpoint);
      return await apiClient.get(endpoint);
    } catch (error) {
      console.error('Get history error:', error);
      throw error;
    }
  },

  /**
   * 메시지 삭제
   * @param {number} messageId - 메시지 ID
   * @returns {Promise<Object>} - 삭제 결과
   */
  async deleteMessage(messageId) {
    try {
      const endpoint = config.api.endpoints.chat.deleteMessage(messageId);
      console.log('[GeneralChatService] Deleting message:', messageId);
      return await apiClient.delete(endpoint);
    } catch (error) {
      console.error('Delete message error:', error);
      throw error;
    }
  },

  /**
   * 세션 채팅 전체 삭제
   * @param {number} sessionId - 세션 ID
   * @returns {Promise<Object>} - 삭제 결과
   */
  async clearSession(sessionId) {
    try {
      const endpoint = config.api.endpoints.chat.clearSession(sessionId);
      console.log('[GeneralChatService] Clearing session:', sessionId);
      return await apiClient.delete(endpoint);
    } catch (error) {
      console.error('Clear session error:', error);
      throw error;
    }
  },
};

export default generalChatService;
