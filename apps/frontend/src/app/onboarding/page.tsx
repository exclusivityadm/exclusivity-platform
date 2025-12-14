"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { completeOnboarding } from "../lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function finish() {
    setLoading(true);
    try {
      await completeOnboarding();
      router.replace("/dashboard");
    } catch (err) {
      console.error("Failed to complete onboarding", err);
      alert("Setup failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-xl">
      <h1 className="text-2xl font-bold mb-4">Welcome to Exclusivity</h1>
      <p className="mb-6">
        Your store is connected. Finish setup to access your dashboard.
      </p>

      <button
        onClick={finish}
        disabled={loading}
        className="px-6 py-3 bg-black text-white rounded"
      >
        {loading ? "Finalizing…" : "Finish Setup"}
      </button>
    </div>
  );
}
