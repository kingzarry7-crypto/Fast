"use client";

import { useEffect, useRef, useState, type MouseEvent, type PointerEvent } from "react";

type Connection = {
  status?: "login_required" | "human_verification" | "ready_to_confirm" | "connected" | string;
  connected?: boolean;
  login_required?: boolean;
  human_verification_required?: boolean;
  url?: string;
  title?: string;
};

type Page = {
  url?: string;
  title?: string;
  text?: string;
  screenshot?: string;
  viewport?: { width?: number; height?: number };
  human_verification?: { required?: boolean; message?: string; indicators?: string[] };
  connection?: Connection;
  buttons?: { selector?: string | null; text?: string }[];
  inputs?: { selector: string; type: string; name?: string | null; placeholder?: string | null }[];
};

export default function ConnectionsPanel() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [page, setPage] = useState<Page | null>(null);
  const [connection, setConnection] = useState<Connection | null>(null);
  const [busy, setBusy] = useState(false);
  const [selector, setSelector] = useState("");
  const [value, setValue] = useState("");
  const [task, setTask] = useState("");
  const [workflow, setWorkflow] = useState<any>(null);
  const [message, setMessage] = useState("");
  const [challengeBusy, setChallengeBusy] = useState(false);
  const challengePress = useRef<{ x: number; y: number; startedAt: number; pointerId: number } | null>(null);

  useEffect(() => {
    if (!open || !page?.human_verification?.required) return;
    const timer = window.setInterval(async () => {
      if (challengePress.current) return;
      try {
        const r = await fetch("/api/browser/inspect", { credentials: "include" });
        const d = await r.json();
        if (r.ok && d.page) {
          setPage(d.page);
          setConnection(d.page.connection || null);
        }
      } catch {}
    }, 3000);
    return () => window.clearInterval(timer);
  }, [open, page?.human_verification?.required]);

  async function start() {
    if (!url.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const r = await fetch("/api/browser/connect/start", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Could not open account");
      setPage(d.page);
      setConnection(d.page?.connection || null);
      setMessage(
        d.page?.human_verification?.required
          ? "Human verification is required. Complete it yourself in this browser session; KZ will not bypass it."
          : "Login yourself. Email, username, password and OTP values are used only to operate the current browser session and are not saved as KZ memory."
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not connect");
    } finally {
      setBusy(false);
    }
  }

  async function refresh() {
    setBusy(true);
    try {
      const r = await fetch("/api/browser/inspect", { credentials: "include" });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Could not inspect session");
      setPage(d.page);
      setConnection(d.page?.connection || null);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not inspect session");
    } finally {
      setBusy(false);
    }
  }

  async function confirmConnection() {
    setBusy(true);
    setMessage("");
    try {
      const r = await fetch("/api/browser/connect/confirm", {
        method: "POST",
        credentials: "include",
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "The account is not ready");
      setConnection(d.connection);
      setMessage("ACCOUNT CONNECTED. KZ can now prepare approved tasks for this browser session.");
      await refresh();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not confirm account");
    } finally {
      setBusy(false);
    }
  }

  async function action(type: string) {
    setBusy(true);
    try {
      const button =
        type === "click"
          ? (page?.buttons || []).find(
              (x) => x.selector === selector || (!x.selector && selector === "__text__:" + x.text)
            )
          : null;
      const payload = {
        type,
        selector: button?.selector || (type === "click" && button ? undefined : selector),
        value,
        text: button?.text || undefined,
      };
      const r = await fetch("/api/browser/connect/action", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Action failed");
      setPage(d.page);
      setConnection(d.page?.connection || null);
      if (type === "fill") setValue("");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  function challengeCoordinates(event: MouseEvent<HTMLImageElement>) {
    const image = event.currentTarget;
    const rect = image.getBoundingClientRect();
    const viewportWidth = Number(page?.viewport?.width || 1440);
    const viewportHeight = Number(page?.viewport?.height || 900);
    return {
      x: Math.max(0, Math.min(viewportWidth, ((event.clientX - rect.left) / rect.width) * viewportWidth)),
      y: Math.max(0, Math.min(viewportHeight, ((event.clientY - rect.top) / rect.height) * viewportHeight)),
    };
  }

  async function clickLiveBrowser(event: PointerEvent<HTMLImageElement>) {
    if (!page?.screenshot || page.human_verification?.required || challengeBusy || busy) return;
    const { x, y } = challengeCoordinates(event as unknown as MouseEvent<HTMLImageElement>);
    try {
      const r = await fetch("/api/browser/connect/action", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "manual_click", x, y }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Browser click failed");
      setPage(d.page);
      setConnection(d.page?.connection || null);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Browser click failed");
    }
  }

  async function checkHumanVerification() {
    setChallengeBusy(true);
    setMessage("CHECKING: waiting for Fiverr to report the result...");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const r = await fetch("/api/browser/connect/action", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "human_verify" }),
        signal: controller.signal,
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || "Verification check failed");
      setPage(d.page);
      setConnection(d.page?.connection || null);
      if (d.result?.verified) {
        setMessage("✓ VERIFIED — Fiverr's human-verification challenge has cleared. KZ is now checking your actual login session.");
      } else {
        setMessage("NOT VERIFIED — Fiverr is still reporting the human-verification challenge. Complete it, wait for it to finish, then press CHECK VERIFICATION again.");
      }
    } catch (e) {
      setMessage(
        e instanceof DOMException && e.name === "AbortError"
          ? "CHECK FAILED — Fiverr did not respond to the verification check within 15 seconds. Press REFRESH VIEW and try CHECK VERIFICATION again."
          : e instanceof Error
            ? "CHECK FAILED — " + e.message
            : "CHECK FAILED — Could not check verification."
      );
    } finally {
      window.clearTimeout(timeout);
      setChallengeBusy(false);
    }
  }

  function beginHumanPress(event: PointerEvent<HTMLImageElement>) {
    if (!page?.human_verification?.required || !page.screenshot || challengePress.current) return;
    const { x, y } = challengeCoordinates(event as unknown as MouseEvent<HTMLImageElement>);
    challengePress.current = { x, y, startedAt: performance.now(), pointerId: event.pointerId };
    event.currentTarget.setPointerCapture?.(event.pointerId);
    event.preventDefault();
    setMessage("Holding the challenge control… release when Fiverr accepts the press.");
  }

  async function finishHumanPress(event: PointerEvent<HTMLImageElement>) {
    const press = challengePress.current;
    if (!press || press.pointerId !== event.pointerId) return;
    challengePress.current = null;
    event.preventDefault();
    try { event.currentTarget.releasePointerCapture?.(event.pointerId); } catch {}

    const durationMs = Math.max(100, Math.min(Math.round(performance.now() - press.startedAt), 15000));
    setChallengeBusy(true);
    try {
      const r = await fetch("/api/browser/connect/action", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "human_press", x: press.x, y: press.y, duration_ms: durationMs }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Manual browser interaction failed");
      setPage(d.page);
      setConnection(d.page?.connection || null);
      setMessage(
        d.result?.verified
          ? "✓ VERIFIED — Fiverr's challenge cleared. KZ is now checking the real login session."
          : "NOT VERIFIED — Fiverr's challenge is still active. Try the press-and-hold again exactly as Fiverr requests."
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Manual browser interaction failed");
    } finally {
      setChallengeBusy(false);
    }
  }

  function cancelHumanPress(event: PointerEvent<HTMLImageElement>) {
    if (!challengePress.current || challengePress.current.pointerId !== event.pointerId) return;
    challengePress.current = null;
    try { event.currentTarget.releasePointerCapture?.(event.pointerId); } catch {}
    setMessage("Challenge press cancelled. Press and hold the control again.");
  }

  async function createTask() {
    if (!task.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const r = await fetch("/api/browser/connect/task", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: task.trim() }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || "Could not create task");
      setWorkflow(d.workflow);
      setMessage(
        d.workflow?.status === "waiting_for_approval"
          ? "TASK READY FOR APPROVAL. KZ will not perform the consequential action until you approve it."
          : "Task created and prepared."
      );
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not create task");
    } finally {
      setBusy(false);
    }
  }

  const status = connection?.status || page?.connection?.status || "not_connected";
  const statusLabel =
    status === "connected"
      ? "CONNECTED"
      : status === "human_verification"
        ? "HUMAN VERIFICATION"
        : status === "login_required"
          ? "LOGIN REQUIRED"
          : status === "ready_to_confirm"
            ? "READY TO CONFIRM"
            : "NOT CONNECTED";

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md border border-cyan-400/30 bg-cyan-400/5 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-cyan-200 hover:bg-cyan-400/10"
      >
        ACCOUNTS
      </button>

      {open && (
        <>
          <button className="fixed inset-0 z-[70] bg-black/60" aria-label="Close accounts" onClick={() => setOpen(false)} />
          <aside className="fixed right-0 top-0 z-[80] flex h-[100dvh] w-full max-w-md flex-col border-l border-cyan-400/20 bg-[#060811] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
              <div>
                <div className="font-mono-tech text-xs tracking-[0.2em] text-cyan-200">CONNECTED ACCOUNTS · LOGIN DASHBOARD</div>
                <div className="mt-1 text-[10px] text-zinc-500">
                  Log in yourself inside the browser below. KZ only marks the account connected after the live session shows authenticated evidence; it will not guess from an open page.
                </div>
              </div>
              <button onClick={() => setOpen(false)} className="px-2 py-1 text-zinc-500">×</button>
            </div>

            <div className="border-b border-white/5 p-4">
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://your-site.com/login"
                className="w-full rounded-lg border border-cyan-400/15 bg-white/[0.03] p-3 text-sm text-white outline-none"
              />
              <button
                disabled={busy || !url.trim()}
                onClick={start}
                className="mt-2 w-full rounded-lg border border-cyan-400/25 bg-cyan-400/10 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-100 disabled:opacity-40"
              >
                {busy ? "OPENING..." : "OPEN LOGIN"}
              </button>

              {connection && (
                <div className="mt-3 rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-mono-tech text-[9px] tracking-widest text-zinc-500">ACCOUNT STATE</span>
                    <span className="font-mono-tech text-[9px] tracking-widest text-cyan-200">{statusLabel}</span>
                  </div>
                  <div className="mt-1 truncate text-[10px] text-zinc-600">{connection.url}</div>
                </div>
              )}

              {message && <p className="mt-2 text-xs leading-relaxed text-zinc-400">{message}</p>}
            </div>

            {page && (
              <div className="min-h-0 flex-1 overflow-y-auto p-4">
                {!page.human_verification?.required && page.screenshot && (
                  <div className="mb-3 rounded-lg border border-cyan-400/20 bg-black p-2">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="font-mono-tech text-[9px] tracking-widest text-cyan-200">LIVE LOGIN BROWSER</span>
                      <span className="text-[9px] text-zinc-600">Click the browser yourself</span>
                    </div>
                    <img
                      src={page.screenshot}
                      alt="Live KZ browser login view"
                      onPointerUp={(event) => {
                        event.preventDefault();
                        void clickLiveBrowser(event);
                      }}
                      draggable={false}
                      style={{ touchAction: "none", userSelect: "none" }}
                      className="block h-auto w-full cursor-pointer select-none"
                    />
                    <p className="mt-2 text-[10px] leading-relaxed text-zinc-600">
                      Use this live browser to choose login controls yourself. Enter email/password in the fields below; KZ does not solve verification challenges.
                    </p>
                  </div>
                )}

                {page.human_verification?.required && (
                  <div className="mb-3 rounded-lg border border-amber-400/30 bg-amber-400/5 p-3">
                    <div className="font-mono-tech text-[10px] tracking-widest text-amber-200">HUMAN VERIFICATION REQUIRED</div>
                    <p className="mt-1 text-xs leading-relaxed text-amber-100/80">
                      {page.human_verification.message || "Complete the challenge yourself. KZ will not bypass it."}
                    </p>
                    <p className="mt-2 text-[10px] leading-relaxed text-amber-100/60">
                      The server browser is shown below. Complete the challenge yourself exactly as Fiverr asks. KZ forwards only your manual press/hold input; it does not solve or bypass the challenge.
                    </p>
                    {page.screenshot && (
                      <div className="mt-3 overflow-hidden rounded-lg border border-amber-400/20 bg-black">
                        <img
                          src={page.screenshot}
                          alt="Live KZ browser view for manual human verification"
                          onPointerDown={beginHumanPress}
                          onPointerUp={finishHumanPress}
                          onPointerCancel={cancelHumanPress}
                          onLostPointerCapture={cancelHumanPress}
                          draggable={false}
                          style={{ touchAction: "none", userSelect: "none" }}
                          className={"block h-auto w-full cursor-crosshair " + (challengeBusy ? "opacity-60" : "")}
                        />
                      </div>
                    )}
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      <button onClick={checkHumanVerification} disabled={busy || challengeBusy} className="rounded-lg border border-amber-400/30 bg-amber-400/10 py-2 font-mono-tech text-[9px] tracking-widest text-amber-100 disabled:opacity-40">
                        {challengeBusy ? "CHECKING..." : "CHECK VERIFICATION"}
                      </button>
                      <button onClick={refresh} disabled={busy || challengeBusy} className="rounded-lg border border-amber-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-amber-200 disabled:opacity-40">
                        REFRESH VIEW
                      </button>
                    </div>
                  </div>
                )}

                {status !== "connected" && !page.human_verification?.required && (
                  <div className="space-y-2">
                    <button
                      onClick={refresh}
                      disabled={busy}
                      className="w-full rounded-lg border border-cyan-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-200 disabled:opacity-40"
                    >
                      {busy ? "CHECKING LIVE SESSION..." : "VERIFY LOGIN"}
                    </button>
                    <button
                      onClick={confirmConnection}
                      disabled={busy || status !== "ready_to_confirm"}
                      className="w-full rounded-lg border border-cyan-400/30 bg-cyan-400/10 py-3 font-mono-tech text-[10px] tracking-widest text-cyan-100 disabled:opacity-40"
                    >
                      {status === "login_required"
                        ? "LOGIN REQUIRED"
                        : status === "ready_to_confirm"
                          ? "LOGIN VERIFIED — CONNECT ACCOUNT"
                          : "CHECKING LOGIN..."}
                    </button>
                    <p className="text-[10px] leading-relaxed text-zinc-600">
                      KZ will never display CONNECTED merely because this website opened. The live browser must first show authenticated evidence.
                    </p>
                  </div>
                )}

                {status === "connected" && (
                  <div className="rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-3">
                    <div className="font-mono-tech text-[10px] tracking-widest text-cyan-200">ACCOUNT READY</div>
                    <p className="mt-1 text-xs text-zinc-500">Give KZ the task you want performed inside this account.</p>
                    <textarea
                      value={task}
                      onChange={(e) => setTask(e.target.value)}
                      placeholder="Example: Find the best matching opportunity and prepare the application. Do not submit until I approve."
                      className="mt-3 min-h-24 w-full rounded-lg border border-white/10 bg-black/20 p-3 text-sm text-white outline-none"
                    />
                    <button
                      onClick={createTask}
                      disabled={busy || !task.trim()}
                      className="mt-2 w-full rounded-lg border border-cyan-400/25 bg-cyan-400/10 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-100 disabled:opacity-40"
                    >
                      {busy ? "PREPARING..." : "PLAN TASK"}
                    </button>
                    {workflow && (
                      <div className="mt-3 rounded-lg border border-white/5 p-3 text-xs text-zinc-400">
                        <div>Workflow: <span className="text-cyan-200">{workflow.id}</span></div>
                        <div className="mt-1">Status: <span className="text-cyan-200">{workflow.status}</span></div>
                        {workflow.status === "waiting_for_approval" && (
                          <div className="mt-2 text-amber-200">Open the approval queue to approve or reject the consequential action.</div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-3 rounded-lg border border-white/5 bg-white/[0.02] p-3">
                  <div className="truncate text-xs text-cyan-200">{page.title || "Connected page"}</div>
                  <div className="mt-1 break-all text-[9px] text-zinc-600">{page.url}</div>
                </div>

                <div className="mt-3 space-y-2">
                  {(page.buttons || []).filter((x) => x.text).map((x, i) => (
                    <button
                      key={"b" + i}
                      onClick={() => setSelector(x.selector || "__text__:" + x.text)}
                      className={
                        "block w-full rounded-lg border p-2 text-left text-xs " +
                        (selector === x.selector
                          ? "border-amber-400/40 bg-amber-400/10 text-amber-100"
                          : "border-white/5 text-zinc-500")
                      }
                    >
                      BUTTON · {x.text}
                    </button>
                  ))}
                  {(page.inputs || []).map((x, i) => (
                    <button
                      key={i}
                      onClick={() => setSelector(x.selector)}
                      className={
                        "block w-full rounded-lg border p-2 text-left text-xs " +
                        (selector === x.selector
                          ? "border-cyan-400/40 bg-cyan-400/10 text-cyan-100"
                          : "border-white/5 text-zinc-500")
                      }
                    >
                      {x.type} · {x.name || x.placeholder || x.selector}
                    </button>
                  ))}
                </div>

                {selector && (
                  <div className="mt-3 rounded-lg border border-cyan-400/15 p-3">
                    <div className="font-mono-tech text-[9px] tracking-widest text-cyan-300">BROWSER FIELD</div>
                    <div className="mt-1 text-[10px] text-zinc-600">The value is sent only to the current browser action; KZ does not write it to memory.</div>
                    <input
                      value={value}
                      onChange={(e) => setValue(e.target.value)}
                      type={page.inputs?.find((x) => x.selector === selector)?.type === "password" ? "password" : "text"}
                      placeholder="Enter value"
                      className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 p-2 text-sm text-white"
                      autoComplete="off"
                    />
                    <button
                      onClick={() => action("fill")}
                      disabled={busy}
                      className="mt-2 w-full rounded-lg border border-cyan-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-200"
                    >
                      FILL CURRENT FIELD
                    </button>
                  </div>
                )}

                <div className="mt-3 flex gap-2">
                  <button onClick={refresh} disabled={busy} className="flex-1 rounded-lg border border-white/10 py-2 font-mono-tech text-[9px] tracking-widest text-zinc-400">REFRESH</button>
                  <button onClick={() => action("click")} disabled={busy || !selector} className="flex-1 rounded-lg border border-amber-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-amber-200">CLICK SELECTED</button>
                </div>

                <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-white/5 bg-black/20 p-3 text-[10px] text-zinc-500">{page.text || ""}</pre>
              </div>
            )}
          </aside>
        </>
      )}
    </>
  );
}
