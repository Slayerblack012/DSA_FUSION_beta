import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  // Performance optimizations
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  images: { unoptimized: true }, // Required for static export
  experimental: {
    optimizePackageImports: ["lucide-react", "framer-motion"],
  },
};

export default nextConfig;
