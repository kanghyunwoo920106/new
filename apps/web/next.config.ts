import type { NextConfig } from "next";

/** Backend used by Next rewrites (SSR/proxy). Overridden at build/runtime for Docker. */
const apiInternal = process.env.API_INTERNAL_BASE || "http://127.0.0.1:8471";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiInternal}/api/:path*` },
      { source: "/health", destination: `${apiInternal}/health` },
    ];
  },
};

export default nextConfig;
