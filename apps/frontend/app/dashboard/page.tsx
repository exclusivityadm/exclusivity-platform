import { Suspense } from "react";
import DashboardRoot from "../../components/dashboard/DashboardRoot";

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6 text-sm text-gray-500">
          Loading dashboard…
        </div>
      }
    >
      <DashboardRoot />
    </Suspense>
  );
}
