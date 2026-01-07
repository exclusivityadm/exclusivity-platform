// apps/frontend/app/onboarding/page.tsx
// =====================================================
// Exclusivity — Onboarding (FINAL, DYNAMIC)
// Fixes Next.js static prerender bailout permanently
// =====================================================

export const dynamic = "force-dynamic";

import { Suspense } from "react";
import OnboardingClient from "./onboarding-client";

export default function OnboardingPage() {
  return (
    <Suspense fallback={<Loading />}>
      <OnboardingClient />
    </Suspense>
  );
}

function Loading() {
  return (
    <div style={{ padding: 32 }}>
      <h1>Exclusivity — Onboarding</h1>
      <p>Initializing…</p>
    </div>
  );
}
