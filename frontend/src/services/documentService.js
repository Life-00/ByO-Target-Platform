/**
 * Document Service
 * 문서 관리 API 호출
 */

import apiClient from "./apiClient";
import config from "../config/config";

const documentService = {
  /**
   * 문서 업로드
   * @param {File} file - PDF 파일
   * @param {string} title - 문서 제목
   * @param {string} description - 문서 설명 (선택)
   * @param {number} sessionId - 세션 ID (선택)
   * @returns {Promise<Object>} - 업로드된 문서 정보
   */
  async uploadDocument(file, title, description = "", sessionId = null) {
    try {
      const formData = new FormData();
      formData.append("file", file);

      // Query parameters로 전달
      const params = new URLSearchParams();
      params.append("title", title);
      if (description) {
        params.append("description", description);
      }
      if (sessionId) {
        params.append("session_id", sessionId);
      }

      const endpoint = `${config.api.endpoints.documents.upload}?${params.toString()}`;

      // 직접 fetch 사용 (FormData는 Content-Type을 자동으로 설정해야 함)
      const accessToken = localStorage.getItem("access_token");
      const headers = {};

      if (accessToken) {
        headers.Authorization = `Bearer ${accessToken}`;
      }
      // Content-Type을 설정하지 않음 (FormData가 자동으로 multipart/form-data로 설정)

      const response = await fetch(`${config.api.apiUrl}${endpoint}`, {
        method: "POST",
        headers: headers,
        body: formData,
      });

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
      console.error("Document upload error:", error);
      throw error;
    }
  },

  /**
   * 문서 목록 조회
   * @param {number} limit - 가져올 개수
   * @param {number} offset - 시작 위치
   * @param {number} sessionId - 세션 ID (선택사항, 세션별 문서만 조회)
   * @returns {Promise<Object>} - 문서 목록
   */
  async getDocuments(limit = 50, offset = 0, sessionId = null) {
    try {
      let endpoint;

      if (sessionId) {
        // 세션별 문서 조회
        endpoint = `${config.api.endpoints.documents.session}/${sessionId}?limit=${limit}&offset=${offset}`;
      } else {
        // 전체 문서 조회
        endpoint = `${config.api.endpoints.documents.list}?limit=${limit}&offset=${offset}`;
      }

      return await apiClient.get(endpoint);
    } catch (error) {
      console.error("Get documents error:", error);
      throw error;
    }
  },

  /**
   * 문서 상세 조회
   * @param {number} documentId - 문서 ID
   * @returns {Promise<Object>} - 문서 상세 정보
   */
  async getDocument(documentId) {
    try {
      const endpoint = config.api.endpoints.documents.get(documentId);
      return await apiClient.get(endpoint);
    } catch (error) {
      console.error("Get document error:", error);
      throw error;
    }
  },

  /**
   * 문서 삭제
   * @param {number} documentId - 문서 ID
   * @returns {Promise<Object>} - 삭제 결과
   */
  async deleteDocument(documentId) {
    try {
      const endpoint = config.api.endpoints.documents.delete(documentId);
      return await apiClient.delete(endpoint);
    } catch (error) {
      console.error("Delete document error:", error);
      throw error;
    }
  },

  /**
   * 문서 다운로드 URL 생성 (Blob URL)
   * @param {number} documentId - 문서 ID
   * @returns {Promise<string>} - Blob URL (인증 토큰 포함)
   */
  async getDownloadUrl(documentId) {
    try {
      const accessToken = localStorage.getItem("access_token");
      const endpoint = config.api.endpoints.documents.download(documentId);

      const headers = {};
      if (accessToken) {
        headers.Authorization = `Bearer ${accessToken}`;
      }

      const response = await fetch(`${config.api.apiUrl}${endpoint}`, {
        headers: headers,
      });

      if (!response.ok) {
        throw new Error(`Failed to download document: ${response.status}`);
      }

      // Blob URL 생성 (iframe에서 직접 사용 가능)
      const blob = await response.blob();
      return URL.createObjectURL(blob);
    } catch (error) {
      console.error("Download document error:", error);
      throw error;
    }
  },
};

export default documentService;
