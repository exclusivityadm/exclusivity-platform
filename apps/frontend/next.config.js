/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,

  // REQUIRED for Shopify embedded apps
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value:
              "frame-ancestors https://admin.shopify.com https://*.myshopify.com;",
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
