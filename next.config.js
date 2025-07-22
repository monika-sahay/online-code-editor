/** @type {import('next').NextConfig} */
const nextConfig = {
    allowedDevOrigins: [
      "https://2jfjkj-8000.csb.app",
      "http://localhost:8000",
      "http://localhost:8001",
      "http://localhost:3000",
      "http://127.0.0.1:8000",
      "http://127.0.0.1:3000",
      "http://172.17.0.2:8000",
      "https://online-code-editor-nine-chi.vercel.app",
    ],
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.pexels.com',
        pathname: '/photos/**',
      },
    ],
  },
};

module.exports = nextConfig;
