"use client";

import ProtectedRoute from "@/components/ProtectedRoute";

export default function SignalsPage() {
  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10">
        <h1 className="font-display text-2xl font-bold text-white tracking-wider mb-4">
          Signals
        </h1>
        <p className="text-cyan-400/60 text-sm">
          MTF signals view — wire live signals in a follow-up task.
        </p>
      </div>
    </ProtectedRoute>
  );
}
