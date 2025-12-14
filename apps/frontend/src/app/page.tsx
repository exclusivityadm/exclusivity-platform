"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { SETTINGS } from "@/app/lib/settings";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (!SETTINGS.betaMode) {
      router.push("/maintenance");
      return;
    }

    router.push("/onboarding");
  }, [router]);

  return null;
}
