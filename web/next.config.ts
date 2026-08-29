import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  agentRules: false,
};

if (process.env.NIGHTDESK_EXPORT === "1") {
  nextConfig.output = "export";
}

export default nextConfig;
