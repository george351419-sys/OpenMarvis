/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: { serverComponentsExternalPackages: [] },
  transpilePackages: ["@openmarvis/protocol"],
};
module.exports = nextConfig;
