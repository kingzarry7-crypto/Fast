"use client";

import { useEffect, useState } from "react";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function isIOS() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

function isStandalone() {
  return window.matchMedia("(display-mode: standalone)").matches ||
    Boolean((navigator as Navigator & { standalone?: boolean }).standalone);
}

export default function InstallApp() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const [ios, setIos] = useState(false);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {});
    }

    if (isStandalone()) return;

    const iosDevice = isIOS();
    setIos(iosDevice);

    const handler = (event: Event) => {
      event.preventDefault();
      setDeferred(event as BeforeInstallPromptEvent);
      setVisible(true);
    };

    window.addEventListener("beforeinstallprompt", handler);

    // iPhone/iPad never fire beforeinstallprompt. Show a manual install guide.
    const timer = window.setTimeout(() => setVisible(true), iosDevice ? 800 : 1800);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("beforeinstallprompt", handler);
    };
  }, []);

  if (!visible || isStandalone()) return null;

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    const choice = await deferred.userChoice;
    setVisible(false);
    if (choice.outcome === "accepted") setDeferred(null);
  };

  return (
    <div className="fixed bottom-4 left-1/2 z-[100] w-[calc(100%-20px)] max-w-md -translate-x-1/2 rounded-2xl border border-cyan-400/30 bg-[#020914]/[.97] p-3 shadow-2xl backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <img src="/icon.svg" alt="KING ZARRY AI" className="h-11 w-11 shrink-0 rounded-xl border border-cyan-400/30" />
        <div className="min-w-0 flex-1">
          <div className="font-mono-tech text-[10px] tracking-widest text-cyan-300">KING ZARRY AI APP</div>
          <div className="mt-0.5 text-[11px] text-zinc-400">
            {ios ? "Add KZ AI to your iPhone/iPad Home Screen." : deferred ? "Install KZ AI like a normal mobile app." : "Use your browser menu to install KZ AI."}
          </div>
        </div>
        <button onClick={() => setVisible(false)} aria-label="Close" className="px-1 text-lg text-zinc-500">×</button>
      </div>

      {ios ? (
        <div className="mt-3 rounded-xl border border-cyan-400/15 bg-cyan-400/5 p-3 text-[10px] leading-relaxed text-zinc-300">
          <b className="text-cyan-300">iPhone / iPad:</b> tap <b>Share</b> in Safari → <b>Add to Home Screen</b> → <b>Add</b>.
          <div className="mt-1 text-zinc-500">If “Add to Home Screen” is missing, make sure this page is open in Safari, not an in-app browser.</div>
        </div>
      ) : deferred ? (
        <button onClick={install} className="mt-3 w-full rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-3 py-2 font-mono-tech text-[10px] tracking-widest text-cyan-200">
          INSTALL KZ AI
        </button>
      ) : (
        <div className="mt-3 rounded-xl border border-cyan-400/15 bg-cyan-400/5 p-3 text-[10px] leading-relaxed text-zinc-300">
          <b className="text-cyan-300">Android / Chrome:</b> open the browser <b>⋮</b> menu → <b>Install app</b> or <b>Add to Home screen</b>.
          <div className="mt-1 text-zinc-500">The app must be opened from the HTTPS Vercel site for installation to be available.</div>
        </div>
      )}
    </div>
  );
}
