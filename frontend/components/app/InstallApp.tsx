"use client";

import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

export default function InstallApp() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }

    const handler = (event: Event) => {
      event.preventDefault();
      setDeferred(event as BeforeInstallPromptEvent);
      setVisible(true);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  if (!visible || !deferred) return null;

  const install = async () => {
    await deferred.prompt();
    const choice = await deferred.userChoice;
    setVisible(false);
    if (choice.outcome === "accepted") setDeferred(null);
  };

  return (
    <div className="fixed bottom-4 left-1/2 z-[100] flex w-[calc(100%-24px)] max-w-sm -translate-x-1/2 items-center gap-3 rounded-2xl border border-cyan-400/30 bg-[#020914]/95 p-3 shadow-2xl backdrop-blur-xl">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-400/30 bg-cyan-400/10 text-lg">
        🤖
      </div>
      <div className="min-w-0 flex-1">
        <div className="font-mono-tech text-[10px] tracking-widest text-cyan-300">KING ZARRY AI APP</div>
        <div className="text-[11px] text-zinc-400">Install KZ AI on your phone.</div>
      </div>
      <button
        onClick={install}
        className="rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-3 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-200"
      >
        INSTALL
      </button>
      <button
        onClick={() => setVisible(false)}
        aria-label="Close"
        className="px-1 text-zinc-500"
      >
        ×
      </button>
    </div>
  );
}
