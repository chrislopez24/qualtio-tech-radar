import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  distDir: 'dist',
  basePath: '/qualtio-tech-radar',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
