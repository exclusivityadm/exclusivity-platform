"use client";

import { ReactNode, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { AppProvider } from "@shopify/app-bridge-react";

export default function RootLayout({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();

  const apiKey =
    process.env.NEXT_PUBLIC_SHOPIFY_API_KEY ??
    process.env.NEXT_PUBLIC_SHOPIFY_CLIENT_ID ??
    "";

  const host = searchParams.get("host");

  useEffect(() => {
    // If Shopify loads us without host param, force reload inside iframe
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (!params.get("embedded")) {
        params.set("embedded", "1");
        window.location.search = params.toString();
      }
    }
  }, []);

  if (!apiKey || !host) {
    // Render minimal shell instead of crashing iframe
    return (
      <html>
        <body className="bg-neutral-950 text-neutral-50">
          <div className="p-6 text-sm opacity-70">
            Loading Shopify context…
          </div>
        </body>
      </html>
    );
  }

  return (
    <html>
      <body className="bg-neutral-950 text-neutral-50">
        <AppProvider
          options={{
            apiKey,
            host,
            forceRedirect: true,
          }}
        >
          {children}
        </AppProvider>
      </body>
    </html>
  );
}
