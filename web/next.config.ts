import type { NextConfig } from "next";

const mock =
  process.env.API_MODE === "mock" ||
  (process.env.API_MODE !== "live" && process.env.NODE_ENV === "development");
// STATIC_EXPORT=1 builds plain files for a single Vercel project that also serves the Python /api.
const staticExport = process.env.STATIC_EXPORT === "1";
const backend = mock ? "http://127.0.0.1:4311" : process.env.BACKEND_ORIGIN;

const config: NextConfig = {
  env: { NEXT_PUBLIC_API_MODE: mock ? "mock" : "live" },
  poweredByHeader: false,
  ...(staticExport ? { output: "export" as const } : {}),
  async rewrites() {
    return backend && !staticExport
      ? [
          {
            source: "/api/:path*",
            destination: `${backend.replace(/\/$/, "")}/api/:path*`,
          },
        ]
      : [];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};
export default config;
