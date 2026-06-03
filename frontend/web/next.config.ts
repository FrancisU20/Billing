import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Static export para CloudFront/S3
  // Correcto para un SaaS dashboard 100% client-side — no requiere SSR
  output: "export",
  trailingSlash: true,
  // Variables de entorno — se hornean en el build en tiempo de compilación
  // Los valores se inyectan en CI/CD desde los outputs de CloudFormation (no hardcodeados)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
    NEXT_PUBLIC_COGNITO_USER_POOL_ID: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID || "",
    NEXT_PUBLIC_COGNITO_CLIENT_ID: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID || "",
    NEXT_PUBLIC_COGNITO_REGION: process.env.NEXT_PUBLIC_COGNITO_REGION || "sa-east-1",
  },
  // Deshabilitar image optimization (no disponible en static export)
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
