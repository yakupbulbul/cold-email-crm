import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    // In production, Nginx handles /api/ proxying.
    // In local dev (npm run dev), proxy to backend container.
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8050";
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
