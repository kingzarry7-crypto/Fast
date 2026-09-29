"use client";

import ProtectedRoute from "@/components/ProtectedRoute";
import ChatWorkspace from "@/components/chat/ChatWorkspace";

export default function ChatPage() {
  return (
    <ProtectedRoute>
      <ChatWorkspace fullScreen />
    </ProtectedRoute>
  );
}
