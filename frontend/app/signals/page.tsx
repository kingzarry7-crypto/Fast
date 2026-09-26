"use client";

import ProtectedRoute from "@/components/ProtectedRoute";

export default function SignalsPage() {
  return (
    <ProtectedRoute>
      <div className="p-6 lg:p-10 max-w-5xl mx-auto">
        <h1 className="font-display text-2xl font-bold text-white kz-glow-text mb-2 tracking-wider">
          Signals
        </h1>
        <p className="font-mono-tech text-[10px] tracking-[0.4em] text-cyan-400/40 mb-8">
          TRADING SIGNAL MODULE
        </p>
        <div className="kz-panel p-10 text-center">
          <p className="text-sm text-cyan-200/50 font-mono-tech tracking-wider">
            Signals module ready. Backend integration pending.
          </p>
          <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/30 mt-3">
            AWAITING API ENDPOINT
          </p>
        </div>
      </div>
    </ProtectedRoute>
  );
}
