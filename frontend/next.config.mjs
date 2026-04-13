/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  /** Dev: browser calls same-origin `/api/v1/...`; Next forwards to FastAPI (avoids CORS). */
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },
    ];
  },
};

export default nextConfig;
