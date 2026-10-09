"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import VentureCoreDashboard from "@/components/dashboard/VentureCoreDashboard";

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <div className="fixed inset-0 h-[100dvh] w-full overflow-hidden">
        <VentureCoreDashboard />
      </div>
    </ProtectedRoute>
  );
}
