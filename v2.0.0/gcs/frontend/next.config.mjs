/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@heroui/react"],
  experimental: {
    optimizePackageImports: ["@heroui/react", "lucide-react"],
  },
};

export default nextConfig;
