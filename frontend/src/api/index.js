import axios from "axios";

const raw = import.meta.env.VITE_API_BASE_URL;

// dev: http://localhost:8000/api/v1
// prod(nginx proxy): /api/v1
const baseURL =
  (raw && raw.trim()) ||
  (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "/api/v1");

console.log("[FRONT] API baseURL =", baseURL);

const api = axios.create({
  baseURL,
  headers: {
    "Content-Type": "application/json",
  },
});

// token attach
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default api;
