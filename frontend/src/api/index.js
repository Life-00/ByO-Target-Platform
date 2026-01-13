import axios from "axios";

const BASE_URL =
  window._env_?.API_BASE_URL || import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  // 타임아웃 설정 추천 (예: 10초)
  timeout: 10000,
});

// 1. 요청 인터셉터 (토큰 주입)
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      console.warn("세션이 만료되었습니다. 로그아웃 처리합니다.");
      localStorage.removeItem("token");
    }
    return Promise.reject(error);
  }
);

export default api;
