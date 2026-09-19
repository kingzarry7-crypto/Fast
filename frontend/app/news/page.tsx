"use client";

import ProtectedRoute from "@/components/ProtectedRoute";

export default function NewsPage() {
  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-2">News</h1>
        <p className="text-xs font-mono text-cyan-400/40 tracking-widest mb-8">
          NEWS INTELLIGENCE MODULE
        </p>

        <div className="kz-panel p-10 text-center">
          <p className="text-sm text-cyan-200/50">
            News module ready. Backend integration pending.
          </p>
          <p className="text-[10px] font-mono text-cyan-400/30 tracking-widest mt-2">
            AWAITING API ENDPOINT
          </p>
        </div>
      </div>
    </ProtectedRoute>
  );
}
