"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";

/** Chat lives on the dashboard — one surface only */
export default function ChatPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/dashboard");
  }, [router]);

  return (
    <ProtectedRoute>
      <div className="flex h-[100dvh] items-center justify-center bg-[#020914]">
        <p className="font-mono-tech text-[10px] tracking-[0.3em] text-cyan-400/50">
          OPENING COMMAND CENTRE…
        </p>
      </div>
    </ProtectedRoute>
  );
}
