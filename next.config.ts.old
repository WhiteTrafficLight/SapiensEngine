import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  transpilePackages: ["@headlessui/react"],
  reactStrictMode: true,
  swcMinify: true,
  
  // 이미지 도메인 허용
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/portraits/**',
      },
    ],
  },
  
  // API 서버로 리라이트
  async rewrites() {
    return [
      {
        source: '/portraits/:path*',
        destination: 'http://localhost:8000/portraits/:path*',
      },
    ];
  },
};

export default nextConfig; 
 