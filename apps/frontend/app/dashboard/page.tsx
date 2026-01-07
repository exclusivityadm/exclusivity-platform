import { redirect } from "next/navigation";
import { Suspense } from "react";
import DashboardRoot from "@/components/dashboard/DashboardRoot";

interface PageProps {
  searchParams?: {
    merchant_id?: string;
  };
}

export default function DashboardPage({ searchParams }: PageProps) {
  const merchantId = searchParams?.merchant_id;

  // 🔒 Guardrail: merchant context required
  if (!merchantId) {
    redirect("/onboarding");
  }

  return (
    <Suspense fallback={<div className="p-6">Loading dashboard…</div>}>
      <DashboardRoot merchantId={merchantId} />
    </Suspense>
  );
}
