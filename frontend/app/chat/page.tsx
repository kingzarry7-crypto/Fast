"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import ChatWorkspace from "@/components/chat/ChatWorkspace";

/** The dashboard routes chat requests here; keep the actual chat mounted here
 * so the sessionStorage prompt handoff has a live receiver and replies render. */
export default function ChatPage() {
  return (
    <ProtectedRoute>
      <main className="h-[100dvh] w-full overflow-hidden bg-[#020914]">
        <ChatWorkspace fullScreen />
      </main>
    </ProtectedRoute>
  );
}
