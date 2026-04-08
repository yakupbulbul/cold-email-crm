import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    // In production, the external reverse proxy handles /api/ proxying.
    // In local dev, keep the browser on the local frontend origin and proxy to the local backend.
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
