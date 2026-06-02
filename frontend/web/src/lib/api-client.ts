import axios from "axios";
import { getAccessToken } from "./auth";

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: { "Content-Type": "application/json" },
});

// Inyecta el JWT de Cognito en cada request autenticado
apiClient.interceptors.request.use(async (config) => {
  try {
    const token = await getAccessToken();
    config.headers.Authorization = `Bearer ${token}`;
  } catch {
    // Sin sesión activa — el servidor responderá 401
  }
  return config;
});

// Redirige a login si el token expiró
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
