"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { fetchOnboardingStatus } from "@/app/lib/api";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    async function init() {
      try {
        const status = await fetchOnboardingStatus();

        if (status.onboarding_complete) {
          router.replace("/dashboard");
        } else {
          router.replace("/onboarding");
        }
      } catch (err) {
        console.error("Failed to load onboarding status", err);
      }
    }

    init();
  }, [router]);

  return <div className="p-8">Loading Exclusivity…</div>;
}
