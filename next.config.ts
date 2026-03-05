import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  distDir: 'dist',
  // Only use basePath in production (GitHub Pages)
  basePath: process.env.NODE_ENV === 'production' ? '/qualtio-tech-radar' : '',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
