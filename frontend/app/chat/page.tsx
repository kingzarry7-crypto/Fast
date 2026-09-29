"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import ChatWorkspace from "@/components/chat/ChatWorkspace";

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <div className="h-[100dvh] min-h-0 bg-[#020914]">
        <ChatWorkspace fullScreen embedMode={false} />
      </div>
    </ProtectedRoute>
  );
}
