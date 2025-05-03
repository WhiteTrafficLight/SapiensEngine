import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  transpilePackages: ["@headlessui/react"],
  reactStrictMode: true,
  swcMinify: true,
};

export default nextConfig; 
 