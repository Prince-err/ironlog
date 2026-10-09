import type { NextConfig } from "next";

// The browser never talks to FastAPI directly:
// /api/v1/* is proxied server-side to the FastAPI origin.
// API_ORIGIN can be overridden; default is the local dev backend.
const API_ORIGIN = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Allow dev-mode asset/HMR requests from tailnet/LAN origins (phone testing).
  allowedDevOrigins: ["100.83.25.127", "192.168.29.75"],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${API_ORIGIN}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
