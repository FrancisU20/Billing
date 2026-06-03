import axios from "axios";
import { getAccessToken } from "./auth";

// Con Vite las variables de entorno usan el prefijo VITE_
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use(async (config) => {
  try {
    const token = await getAccessToken();
    config.headers.Authorization = `Bearer ${token}`;
  } catch {
    // Sin sesión activa — el servidor responderá 401
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
