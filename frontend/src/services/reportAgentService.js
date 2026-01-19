/**
 * Report Agent Service
 * 연구 타당성 보고서 생성 서비스
 */

import apiClient from "./apiClient";
import authService from "./authService";
import config from "../config/config";

const reportAgentService = {
  /**
   * 보고서 생성 요청
   * @param {string} researchTopic - 연구 주제
   * @param {Object} options - 추가 옵션
   * @param {string} options.researchDescription - 연구 설명
   * @param {string} options.analysisGoal - 분석 목표
   * @param {Array} options.documents - 관련 문서 목록
   * @param {boolean} options.includeVisualizations - 시각화 포함 여부
   * @param {boolean} options.includeNetworkGraph - 네트워크 그래프 포함 여부
   * @param {string} options.reportType - 보고서 형식 (comprehensive, summary, detailed)
   * @param {number} options.temperature - LLM 온도
   * @param {number} options.maxTokens - 최대 토큰
   * @param {string} options.sessionId - 세션 ID (optional)
   * @returns {Promise<Object>} - 생성된 보고서
   */
  async generateReport(researchTopic, options = {}) {
    try {
      const {
        researchDescription = null,
        analysisGoal = null,
        documents = [],
        includeVisualizations = true,
        includeNetworkGraph = true,
        reportType = "comprehensive",
        temperature = 0.7,
        maxTokens = 4096,
        sessionId = null,
      } = options;

      const endpoint = config.api.endpoints.agents.report.generate;

      // 문서 레퍼런스 포맷 변환
      const relatedDocuments = documents.map((doc) => ({
        id: doc.id,
        title: doc.title || doc.name || "Unknown",
        authors: doc.authors || doc.author || null,
        year: doc.year || doc.publication_year || null,
      }));

      const payload = {
        research_topic: researchTopic,
        research_data: {
          topic: researchTopic,
          description: researchDescription,
          analysis_goal: analysisGoal,
          related_documents: relatedDocuments,
        },
        report_type: reportType,
        include_visualizations: includeVisualizations,
        include_network_graph: includeNetworkGraph,
        temperature: temperature,
        max_tokens: maxTokens,
      };

      console.log("[ReportAgentService] Generating report:", payload);

      // 세션 ID가 있으면 쿼리 파라미터로 추가
      const queryParams = sessionId ? `?session_id=${sessionId}` : "";
      const response = await apiClient.post(
        `${endpoint}${queryParams}`,
        payload,
      );

      console.log("[ReportAgentService] Report generated:", response);
      return response;
    } catch (error) {
      console.error("[ReportAgentService] Generate report error:", error);
      throw error;
    }
  },

  /**
   * 빠른 분석 (간단한 타당성 평가)
   * @param {string} topic - 연구 주제
   * @returns {Promise<Object>} - 타당성 분석 결과
   */
  async quickAnalysis(topic) {
    try {
      const endpoint = "/api/v1/agents/report/analyze";
      const payload = { topic };

      console.log("[ReportAgentService] Quick analysis:", payload);
      const response = await apiClient.post(endpoint, payload);

      console.log("[ReportAgentService] Analysis result:", response);
      return response;
    } catch (error) {
      console.error("[ReportAgentService] Quick analysis error:", error);
      throw error;
    }
  },

  /**
   * 보고서 히스토리 조회
   * @param {Object} options - 조회 옵션
   * @param {string} options.sessionId - 세션 ID (optional)
   * @param {number} options.limit - 조회 개수 (1-100)
   * @returns {Promise<Object>} - 보고서 히스토리
   */
  async getHistory(options = {}) {
    try {
      const { sessionId = null, limit = 10 } = options;

      const endpoint = "/api/v1/agents/report/history";
      const params = new URLSearchParams();

      if (sessionId) params.append("session_id", sessionId);
      params.append("limit", limit);

      console.log("[ReportAgentService] Fetching history");
      const response = await apiClient.get(`${endpoint}?${params.toString()}`);

      console.log("[ReportAgentService] History retrieved:", response);
      return response;
    } catch (error) {
      console.error("[ReportAgentService] Get history error:", error);
      throw error;
    }
  },

  /**
   * 보고서 삭제
   * @param {string} reportId - 보고서 ID
   * @returns {Promise<Object>} - 삭제 결과
   */
  async deleteReport(reportId) {
    try {
      const endpoint = `/api/v1/agents/report/delete/${reportId}`;

      console.log("[ReportAgentService] Deleting report:", reportId);
      const response = await apiClient.delete(endpoint);

      console.log("[ReportAgentService] Report deleted:", response);
      return response;
    } catch (error) {
      console.error("[ReportAgentService] Delete report error:", error);
      throw error;
    }
  },

  /**
   * 보고서 다운로드
   * @param {string} reportId - 보고서 ID
   * @param {string} format - 다운로드 형식 (markdown, pdf, json)
   * @returns {Promise<Object>} - 다운로드 URL
   */
  async downloadReport(reportId, format = "markdown") {
    try {
      const endpoint = `/api/v1/agents/report/download/${reportId}`;
      const params = new URLSearchParams({ format });

      console.log("[ReportAgentService] Downloading report:", reportId, format);
      const response = await apiClient.get(`${endpoint}?${params.toString()}`);

      console.log("[ReportAgentService] Download link:", response);
      return response;
    } catch (error) {
      console.error("[ReportAgentService] Download report error:", error);
      throw error;
    }
  },
};

export default reportAgentService;
