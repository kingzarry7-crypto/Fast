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

async function readApiResponse(response: Response): Promise<any> {
  const raw = await response.text();
  if (!raw) throw new Error(`HTTP ${response.status}: empty response from KZ server`);
  try { return JSON.parse(raw); }
  catch {
    const preview = raw.replace(/\s+/g, " ").trim().slice(0, 240);
    throw new Error(`HTTP ${response.status}: KZ server returned a non-JSON response: ${preview}`);
  }
}

export default function ConnectionsPanel() {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [accountId, setAccountId] = useState("default");
  const [accountName, setAccountName] = useState("Primary Account");
  const [savedAccounts, setSavedAccounts] = useState<{ id: string; name: string; url?: string }[]>([]);
  const [github, setGithub] = useState<any>(null);
  const [githubRepos, setGithubRepos] = useState<any[]>([]);
  const [githubOwner, setGithubOwner] = useState("");
  const [githubRepo, setGithubRepo] = useState("");
  const [githubIssueTitle, setGithubIssueTitle] = useState("");
  const [githubIssueBody, setGithubIssueBody] = useState("");
  const [githubApproval, setGithubApproval] = useState<any>(null);
  const [tiktok, setTiktok] = useState<any>(null);
  const [tiktokQr, setTiktokQr] = useState<any>(null);
  const [page, setPage] = useState<Page | null>(null);
  const [connection, setConnection] = useState<Connection | null>(null);
  const [busy, setBusy] = useState(false);
  const [selector, setSelector] = useState("");
  const [value, setValue] = useState("");
  const [task, setTask] = useState("");
  const [workflow, setWorkflow] = useState<any>(null);
  const [message, setMessage] = useState("");
  const [challengeBusy, setChallengeBusy] = useState(false);
  const challengePress = useRef<{ x: number; y: number; startedAt: number; pointerId: number; remoteDown: boolean } | null>(null);
  const scrollBatch = useRef<{ dx: number; dy: number; timer: number | null }>({ dx: 0, dy: 0, timer: null });

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem("kz_connected_accounts");
      const parsed = raw ? JSON.parse(raw) : [];
      if (Array.isArray(parsed) && parsed.length) {
        setSavedAccounts(parsed);
        const active = parsed[0];
        if (active?.id) {
          setAccountId(active.id);
          setAccountName(active.name || "Account");
        }
      }
    } catch {}
  }, []);

  useEffect(() => {
    try { window.localStorage.setItem("kz_connected_accounts", JSON.stringify(savedAccounts)); } catch {}
  }, [savedAccounts]);

  function saveCurrentAccount() {
    const id = accountId.trim() || "default";
    const name = accountName.trim() || "Account";
    const next = [...savedAccounts.filter((x) => x.id !== id), { id, name, url: url.trim() }];
    setSavedAccounts(next);
  }

  function newAccount() {
    const id = "acct_" + crypto.randomUUID().replace(/-/g, "").slice(0, 16);
    setAccountId(id);
    setAccountName("New Account");
    setUrl("");
    setPage(null);
    setConnection(null);
    setWorkflow(null);
    setMessage("New isolated browser account created. Open its login page and sign in yourself.");
  }

  useEffect(() => {
    if (!open || !page?.human_verification?.required) return;
    const timer = window.setInterval(async () => {
      if (challengePress.current) return;
      try {
        const r = await fetch(`/api/browser/inspect?account_id=${encodeURIComponent(accountId)}`, { credentials: "include" });
        const d = await readApiResponse(r);
        if (r.ok && d.page) {
          setPage(d.page);
          setConnection(d.page.connection || null);
        }
      } catch {}
    }, 3000);
    return () => window.clearInterval(timer);
  }, [open, page?.human_verification?.required, accountId]);

  async function refreshOfficialConnectors() {
    try {
      const r = await fetch("/api/connectors/status", { credentials: "include", cache: "no-store" });
      const d = await readApiResponse(r);
      if (r.ok) {
        setGithub(d.github || null);
        setTiktok(d.tiktok || null);
      }
    } catch {}
  }


  async function connectTikTok() {
    window.location.href = "/api/connectors/tiktok/start";
  }

  async function startTikTokQr() {
    setBusy(true);
    try {
      const r = await fetch("/api/connectors/tiktok/qr/start", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Could not start TikTok QR authorization");
      setTiktokQr(d);
      setMessage("Scan this official TikTok authorization QR with your phone. KZ is not receiving your TikTok password.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not start TikTok QR authorization");
    } finally { setBusy(false); }
  }

  useEffect(() => {
    if (!tiktokQr?.session_id || !open) return;
    const timer = window.setInterval(async () => {
      try {
        const r = await fetch("/api/connectors/tiktok/qr/status", {
          method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: tiktokQr.session_id }),
        });
        const d = await readApiResponse(r);
        if (!r.ok) return;
        if (d.status === "connected") {
          setTiktokQr(null);
          setMessage("✓ TikTok connected through the official TikTok authorization flow.");
          await refreshOfficialConnectors();
        } else if (d.status === "expired") {
          setTiktokQr(null);
          setMessage("TikTok QR expired. Start a new QR authorization.");
        }
      } catch {}
    }, 2000);
    return () => window.clearInterval(timer);
  }, [tiktokQr?.session_id, open]);

  async function connectGitHub() {
    window.location.href = "/api/connectors/github/start";
  }

  async function loadGitHubRepos() {
    setBusy(true);
    try {
      const r = await fetch("/api/connectors/github/action", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operation: "list_repositories", payload: {} }),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Could not read GitHub repositories");
      setGithubRepos(d.result?.repositories || []);
      setMessage("✓ GitHub repositories loaded through the authorized connector.");
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not read GitHub repositories"); }
    finally { setBusy(false); }
  }

  async function createGitHubIssue() {
    if (!githubOwner.trim() || !githubRepo.trim() || !githubIssueTitle.trim()) return;
    setBusy(true);
    try {
      const r = await fetch("/api/connectors/github/action", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operation: "create_issue", payload: {
          owner: githubOwner.trim(), repo: githubRepo.trim(),
          title: githubIssueTitle.trim(), body: githubIssueBody.trim()
        }}),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Could not prepare GitHub action");
      setGithubApproval(d);
      setMessage("GitHub action prepared. Nothing has been sent yet — approval is required.");
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not prepare GitHub action"); }
    finally { setBusy(false); }
  }

  async function decideGitHubApproval(approved: boolean) {
    if (!githubApproval?.approval_id) return;
    setBusy(true);
    try {
      const r = await fetch("/api/connectors/github/approve/" + encodeURIComponent(githubApproval.approval_id), {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Could not process approval");
      setGithubApproval(null);
      setMessage(d.status === "completed" && d.verified ? "✓ GitHub action completed and verified." : approved ? "GitHub action was not verified." : "GitHub action rejected.");
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not process approval"); }
    finally { setBusy(false); }
  }

  useEffect(() => {
    if (!open) return;
    void refreshOfficialConnectors();
    const q = new URLSearchParams(window.location.search);
    if ((q.get("connector") === "github" || q.get("connector") === "tiktok") && q.get("connected") === "1") {
      setMessage(q.get("connector") === "tiktok" ? "✓ TikTok connected through official authorization." : "✓ GitHub connected. KZ can use the authorized account without your GitHub password.");
      void refreshOfficialConnectors();
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [open]);

  async function start() {
    if (!url.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const r = await fetch("/api/browser/connect/start", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim(), account_id: accountId }),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Could not open account");
      setPage(d.page);
      setConnection(d.page?.connection || null);
      saveCurrentAccount();
      setMessage(
        d.page?.human_verification?.required
          ? "Human verification is required. Complete it yourself in this browser session; KZ will not bypass it."
          : "Login yourself. Email, username, password and OTP values are used only to operate the current browser session and are not saved as KZ memory."
      );
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not connect"); }
    finally { setBusy(false); }
  }

  async function refresh() {
    setBusy(true);
    try {
      const r = await fetch(`/api/browser/inspect?account_id=${encodeURIComponent(accountId)}`, { credentials: "include", cache: "no-store" });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Could not inspect session");
      setPage(d.page);
      setConnection(d.page?.connection || null);
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not inspect session"); }
    finally { setBusy(false); }
  }

  async function waitForVerificationTransition() {
    // Fiverr may remove the challenge first and rebuild the login page a moment later.
    // Poll the same isolated browser profile instead of taking one stale screenshot.
    const deadline = Date.now() + 12000;
    while (Date.now() < deadline) {
      await new Promise((resolve) => window.setTimeout(resolve, 800));
      try {
        const r = await fetch(`/api/browser/inspect?account_id=${encodeURIComponent(accountId)}`, {
          credentials: "include",
          cache: "no-store",
        });
        const d = await readApiResponse(r);
        if (!r.ok || !d.page) continue;
        setPage(d.page);
        setConnection(d.page.connection || null);
        if (!d.page.human_verification?.required) return d.page;
      } catch {}
    }
    return null;
  }

  async function confirmConnection() {
    setBusy(true);
    setMessage("");
    try {
      const r = await fetch("/api/browser/connect/confirm", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account_id: accountId }),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "The account is not ready");
      setConnection(d.connection);
      setMessage("ACCOUNT CONNECTED. KZ can now prepare approved tasks for this browser session.");
      await refresh();
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not confirm account"); }
    finally { setBusy(false); }
  }

  async function action(type: string) {
    setBusy(true);
    try {
      const button = type === "click"
        ? (page?.buttons || []).find((x) => x.selector === selector || (!x.selector && selector === "__text__:" + x.text))
        : null;
      const payload = {
        type,
        selector: button?.selector || (type === "click" && button ? undefined : selector),
        value,
        text: button?.text || undefined,
      };
      const r = await fetch("/api/browser/connect/action", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...payload, account_id: accountId }),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Action failed");
      setPage(d.page);
      setConnection(d.page?.connection || null);
      if (type === "fill") setValue("");
    } catch (e) { setMessage(e instanceof Error ? e.message : "Action failed"); }
    finally { setBusy(false); }
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

  function queueBrowserScroll(event: React.WheelEvent<HTMLImageElement>) {
    if (!page?.screenshot || busy) return;
    event.preventDefault();
    const batch = scrollBatch.current;
    batch.dx += event.deltaX;
    batch.dy += event.deltaY;
    if (batch.timer !== null) return;
    batch.timer = window.setTimeout(async () => {
      const dx = batch.dx;
      const dy = batch.dy;
      batch.dx = 0;
      batch.dy = 0;
      batch.timer = null;
      if (!dx && !dy) return;
      try {
        const r = await fetch("/api/browser/connect/action", {
          method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "manual_scroll", delta_x: dx, delta_y: dy, account_id: accountId }),
        });
        const d = await readApiResponse(r);
        if (!r.ok) throw new Error(d.detail || "Browser scroll failed");
        if (d.page) {
          setPage(d.page);
          setConnection(d.page.connection || null);
        }
      } catch (e) {
        setMessage(e instanceof Error ? e.message : "Browser scroll failed");
      }
    }, 50);
  }

  async function clickLiveBrowser(event: PointerEvent<HTMLImageElement>) {
    if (!page?.screenshot || page.human_verification?.required || challengeBusy || busy) return;
    const { x, y } = challengeCoordinates(event as unknown as MouseEvent<HTMLImageElement>);
    try {
      const r = await fetch("/api/browser/connect/action", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "manual_click", x, y, account_id: accountId }),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Browser click failed");
      setPage(d.page);
      setConnection(d.page?.connection || null);
    } catch (e) { setMessage(e instanceof Error ? e.message : "Browser click failed"); }
  }

  async function checkHumanVerification() {
    setChallengeBusy(true);
    setMessage("CHECKING: waiting for Fiverr to report the result...");
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const r = await fetch("/api/browser/connect/action", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "human_verify", account_id: accountId }), signal: controller.signal,
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Verification check failed");
      setPage(d.page);
      setConnection(d.page?.connection || null);
      if (d.result?.verified) {
        setMessage("✓ VERIFIED — waiting for Fiverr to restore the live login browser...");
        const recovered = await waitForVerificationTransition();
        if (recovered) {
          setPage(recovered);
          setConnection(recovered.connection || null);
          setMessage("✓ VERIFIED — LOGIN IS NOT COMPLETE. The live browser is restored; scroll and log in yourself. KZ will only show READY TO CONFIRM after authenticated evidence is detected.");
        } else {
          setMessage("✓ HUMAN VERIFICATION CLEARED — Fiverr is still rebuilding the login page. Press REFRESH VIEW once.");
        }
      } else {
        setMessage("NOT VERIFIED — Fiverr is still reporting the human-verification challenge. Complete it, wait for it to finish, then press CHECK VERIFICATION again.");
      }
    } catch (e) {
      setMessage(e instanceof DOMException && e.name === "AbortError"
        ? "CHECK FAILED — Fiverr did not respond to the verification check within 15 seconds. Press REFRESH VIEW and try CHECK VERIFICATION again."
        : e instanceof Error ? "CHECK FAILED — " + e.message : "CHECK FAILED — Could not check verification.");
    } finally {
      window.clearTimeout(timeout);
      setChallengeBusy(false);
    }
  }

  // Press-and-hold is now a real remote press. The previous implementation
  // waited until pointer-up and then sent a single human_press request, which
  // meant the server browser never received the mouse-down while the user was
  // physically holding the control. That broke challenges that require the
  // hold to remain active for their full duration.
  async function beginHumanPress(event: PointerEvent<HTMLImageElement>) {
    if (!page?.human_verification?.required || !page.screenshot || challengePress.current || challengeBusy || busy) return;
    const { x, y } = challengeCoordinates(event as unknown as MouseEvent<HTMLImageElement>);
    const press = { x, y, startedAt: performance.now(), pointerId: event.pointerId, remoteDown: false };
    challengePress.current = press;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    event.preventDefault();
    setChallengeBusy(true);
    setMessage("PRESS STARTED — keep holding the control until the verification accepts it.");

    try {
      const r = await fetch("/api/browser/connect/action", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "human_down", x, y, account_id: accountId }),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Could not start the remote press");
      press.remoteDown = true;
      setMessage("HOLDING — keep your mouse/finger down until the challenge accepts the press.");
    } catch (e) {
      challengePress.current = null;
      try { event.currentTarget.releasePointerCapture?.(event.pointerId); } catch {}
      setChallengeBusy(false);
      setMessage(e instanceof Error ? e.message : "Could not start the remote press");
    }
  }

  async function finishHumanPress(event: PointerEvent<HTMLImageElement>) {
    const press = challengePress.current;
    if (!press || press.pointerId !== event.pointerId) return;
    challengePress.current = null;
    event.preventDefault();
    try { event.currentTarget.releasePointerCapture?.(event.pointerId); } catch {}

    const durationMs = Math.max(100, Math.min(Math.round(performance.now() - press.startedAt), 15000));
    try {
      // Always release a successful remote mouse-down, even if the network
      // request took a little longer than expected.
      const r = await fetch("/api/browser/connect/action", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "human_up", x: press.x, y: press.y, account_id: accountId }),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Could not release the remote press");
      setPage(d.page);
      setConnection(d.page?.connection || null);
      if (!d.page?.human_verification?.required) {
        setMessage("✓ HUMAN VERIFIED — waiting for Fiverr to restore the login page...");
        const recovered = await waitForVerificationTransition();
        if (recovered) {
          setPage(recovered);
          setConnection(recovered.connection || null);
          setMessage("✓ HUMAN VERIFIED — LOGIN IS NOT COMPLETE. The live browser is restored; scroll and log in yourself. KZ will only show READY TO CONFIRM after authenticated evidence is detected.");
        } else {
          await refresh();
          setMessage("✓ HUMAN VERIFICATION CLEARED — the login page is being restored. Press REFRESH VIEW once if Fiverr is still loading.");
        }
      } else {
        setMessage("The challenge is still active. Try the press-and-hold again exactly as Fiverr requests.");
      }
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Could not release the remote press");
    } finally {
      setChallengeBusy(false);
    }
  }

  async function cancelHumanPress(event: PointerEvent<HTMLImageElement>) {
    const press = challengePress.current;
    if (!press || press.pointerId !== event.pointerId) return;
    challengePress.current = null;
    try { event.currentTarget.releasePointerCapture?.(event.pointerId); } catch {}
    event.preventDefault();

    if (press.remoteDown) {
      try {
        await fetch("/api/browser/connect/action", {
          method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "human_up", x: press.x, y: press.y, account_id: accountId }),
        });
      } catch {}
    }
    setChallengeBusy(false);
    setMessage("Challenge press cancelled. Press and hold the control again.");
  }

  async function createTask() {
    if (!task.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const r = await fetch("/api/browser/connect/task", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: task.trim(), account_id: accountId }),
      });
      const d = await readApiResponse(r);
      if (!r.ok) throw new Error(d.detail || "Could not create task");
      setWorkflow(d.workflow);
      setMessage(d.workflow?.status === "waiting_for_approval"
        ? "TASK READY FOR APPROVAL. KZ will not perform the consequential action until you approve it."
        : "Task created and prepared.");
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not create task"); }
    finally { setBusy(false); }
  }

  const status = connection?.status || page?.connection?.status || "not_connected";
  const statusLabel = status === "connected" ? "CONNECTED" : status === "human_verification" ? "HUMAN VERIFICATION" : status === "login_required" ? "LOGIN REQUIRED" : status === "ready_to_confirm" ? "READY TO CONFIRM" : "NOT CONNECTED";

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="rounded-md border border-cyan-400/30 bg-cyan-400/5 px-2.5 py-1.5 font-mono-tech text-[10px] tracking-widest text-cyan-200 hover:bg-cyan-400/10">ACCOUNTS</button>

      {open && (
        <>
          <button className="fixed inset-0 z-[70] bg-black/60" aria-label="Close accounts" onClick={() => setOpen(false)} />
          <aside className="fixed right-0 top-0 z-[80] flex h-[100dvh] w-full max-w-md flex-col border-l border-cyan-400/20 bg-[#060811] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
              <div>
                <div className="font-mono-tech text-xs tracking-[0.2em] text-cyan-200">CONNECTED ACCOUNTS · LOGIN DASHBOARD</div>
                <div className="mt-1 text-[10px] text-zinc-500">Log in yourself inside the browser below. KZ only marks the account connected after the live session shows authenticated evidence; it will not guess from an open page.</div>
              </div>
              <button onClick={() => setOpen(false)} className="px-2 py-1 text-zinc-500">×</button>
            </div>

            <div className="border-b border-white/5 p-4">
              <div className="mb-3 font-mono-tech text-[10px] tracking-[0.18em] text-cyan-200">OFFICIAL CONNECTORS</div>
              <div className="grid gap-2">
                <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium text-white">GitHub</div>
                      <div className="text-[10px] text-zinc-500">{github?.connected ? "AUTHORIZED ACCOUNT CONNECTED" : github?.configured ? "OAuth ready" : "SERVER SETUP REQUIRED"}</div>
                    </div>
                    {!github?.connected && <button onClick={connectGitHub} disabled={!github?.configured || busy} className="rounded-md border border-cyan-400/30 px-3 py-2 text-[9px] tracking-widest text-cyan-200 disabled:opacity-40">CONNECT</button>}
                  </div>
                </div>
                <div className="rounded-lg border border-pink-400/20 bg-pink-400/[0.03] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-medium text-white">TikTok</div>
                      <div className="text-[10px] text-zinc-500">{tiktok?.connected ? "AUTHORIZED ACCOUNT CONNECTED" : tiktok?.configured ? "OAuth + QR ready" : "SERVER SETUP REQUIRED"}</div>
                    </div>
                    {!tiktok?.connected && <div className="flex gap-2">
                      <button onClick={connectTikTok} disabled={!tiktok?.configured || busy} className="rounded-md border border-pink-400/30 px-3 py-2 text-[9px] tracking-widest text-pink-200 disabled:opacity-40">CONNECT</button>
                      <button onClick={startTikTokQr} disabled={!tiktok?.configured || busy} className="rounded-md border border-white/10 px-3 py-2 text-[9px] tracking-widest text-zinc-300 disabled:opacity-40">QR</button>
                    </div>}
                  </div>
                  {tiktokQr?.scan_qrcode_url && (
                    <div className="mt-3 rounded-lg border border-white/10 bg-black/30 p-3 text-center">
                      <img
                        src={`https://quickchart.io/qr?size=240&text=${encodeURIComponent(tiktokQr.scan_qrcode_url)}`}
                        alt="TikTok authorization QR"
                        className="mx-auto h-48 w-48 rounded bg-white p-2"
                      />
                      <div className="mt-2 text-[10px] text-zinc-400">Scan with TikTok on your phone. Status checks automatically.</div>
                      <a href={tiktokQr.scan_qrcode_url} target="_blank" rel="noreferrer" className="mt-2 block break-all text-[9px] text-cyan-300">OPEN AUTHORIZATION LINK</a>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="border-b border-white/5 p-4">
              <div className="mb-2 grid grid-cols-[1fr_auto] gap-2">
                <input value={accountName} onChange={(e) => setAccountName(e.target.value)} placeholder="Account name" className="w-full rounded-lg border border-cyan-400/15 bg-white/[0.03] p-3 text-sm text-white outline-none" />
                <button onClick={newAccount} type="button" className="rounded-lg border border-cyan-400/20 px-3 text-[9px] tracking-widest text-cyan-200">NEW</button>
              </div>
              <div className="mb-2 flex gap-2">
                <select value={accountId} onChange={(e) => {
                  const id = e.target.value;
                  const found = savedAccounts.find((x) => x.id === id);
                  setAccountId(id); setAccountName(found?.name || "Account"); setUrl(found?.url || ""); setPage(null); setConnection(null); setWorkflow(null);
                  setMessage("Switched to an isolated account browser profile.");
                }} className="min-w-0 flex-1 rounded-lg border border-white/10 bg-black/30 p-2 text-xs text-white">
                  {!savedAccounts.length && <option value="default">Primary Account</option>}
                  {savedAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
                <div className="truncate rounded-lg border border-white/5 px-2 py-2 text-[9px] text-zinc-600">{accountId}</div>
              </div>
              <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://your-site.com/login" className="w-full rounded-lg border border-cyan-400/15 bg-white/[0.03] p-3 text-sm text-white outline-none" />
              <button disabled={busy || !url.trim()} onClick={start} className="mt-2 w-full rounded-lg border border-cyan-400/25 bg-cyan-400/10 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-100 disabled:opacity-40">{busy ? "OPENING..." : "OPEN LOGIN"}</button>

              {connection && <div className="mt-3 rounded-lg border border-white/5 bg-white/[0.02] p-3"><div className="flex items-center justify-between"><span className="font-mono-tech text-[9px] tracking-widest text-zinc-500">ACCOUNT STATE</span><span className="font-mono-tech text-[9px] tracking-widest text-cyan-200">{statusLabel}</span></div><div className="mt-1 truncate text-[10px] text-zinc-600">{connection.url}</div></div>}
              {message && <p className="mt-2 text-xs leading-relaxed text-zinc-400">{message}</p>}
            </div>

            <div className="mb-4 rounded-lg border border-cyan-400/20 bg-cyan-400/[0.03] p-3">
              <div className="font-mono-tech text-[10px] tracking-[0.18em] text-cyan-200">OFFICIAL CONNECTORS</div>
              <p className="mt-1 text-[10px] leading-relaxed text-zinc-500">Use provider authorization instead of browser login when KZ has an official connector.</p>
              <div className="mt-3 rounded-lg border border-white/5 bg-black/20 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div><div className="text-sm text-white">GitHub</div><div className="text-[9px] text-zinc-600">{github?.connected ? "CONNECTED" : github?.configured === false ? "BACKEND NOT CONFIGURED" : "READY TO CONNECT"}</div></div>
                  {github?.connected ? <span className="rounded border border-cyan-400/20 px-2 py-1 text-[9px] text-cyan-200">AUTHORIZED</span> : <button onClick={connectGitHub} disabled={busy || github?.configured === false} className="rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-100 disabled:opacity-40">CONNECT GITHUB</button>}
                </div>
                {github?.connected && <div className="mt-3 space-y-2">
                  <button onClick={loadGitHubRepos} disabled={busy} className="w-full rounded-lg border border-white/10 py-2 font-mono-tech text-[9px] tracking-widest text-zinc-300 disabled:opacity-40">READ MY REPOSITORIES</button>
                  {githubRepos.length > 0 && <div className="max-h-28 overflow-auto space-y-1">{githubRepos.map((repo: any) => <button key={repo.full_name} onClick={() => { const p=String(repo.full_name||"").split("/"); setGithubOwner(p[0]||""); setGithubRepo(p[1]||""); }} className="block w-full rounded border border-white/5 px-2 py-1 text-left text-[10px] text-zinc-400 hover:text-cyan-200">{repo.full_name}</button>)}</div>}
                  <div className="border-t border-white/5 pt-3">
                    <div className="font-mono-tech text-[9px] tracking-widest text-amber-200">WORK — APPROVAL REQUIRED</div>
                    <div className="mt-2 grid grid-cols-2 gap-2"><input value={githubOwner} onChange={e=>setGithubOwner(e.target.value)} placeholder="owner" className="rounded border border-white/10 bg-black/20 p-2 text-xs text-white"/><input value={githubRepo} onChange={e=>setGithubRepo(e.target.value)} placeholder="repo" className="rounded border border-white/10 bg-black/20 p-2 text-xs text-white"/></div>
                    <input value={githubIssueTitle} onChange={e=>setGithubIssueTitle(e.target.value)} placeholder="Issue title" className="mt-2 w-full rounded border border-white/10 bg-black/20 p-2 text-xs text-white"/>
                    <textarea value={githubIssueBody} onChange={e=>setGithubIssueBody(e.target.value)} placeholder="What should KZ do?" className="mt-2 min-h-16 w-full rounded border border-white/10 bg-black/20 p-2 text-xs text-white"/>
                    <button onClick={createGitHubIssue} disabled={busy || !githubOwner.trim() || !githubRepo.trim() || !githubIssueTitle.trim()} className="mt-2 w-full rounded-lg border border-amber-400/25 bg-amber-400/5 py-2 font-mono-tech text-[9px] tracking-widest text-amber-100 disabled:opacity-40">PREPARE — ASK BEFORE SEND</button>
                  </div>
                  {githubApproval && <div className="mt-3 rounded border border-amber-400/25 bg-amber-400/5 p-3"><div className="font-mono-tech text-[9px] tracking-widest text-amber-200">APPROVAL REQUIRED</div><div className="mt-1 text-xs text-zinc-400">{githubApproval.operation} → {githubApproval.target}</div><div className="mt-2 flex gap-2"><button onClick={()=>void decideGitHubApproval(false)} disabled={busy} className="flex-1 rounded border border-white/10 py-2 text-[9px] text-zinc-400">REJECT</button><button onClick={()=>void decideGitHubApproval(true)} disabled={busy} className="flex-1 rounded border border-cyan-400/25 bg-cyan-400/10 py-2 text-[9px] text-cyan-100">APPROVE & EXECUTE</button></div></div>}
                </div>}
              </div>
            </div>

            {page && (
              <div className="min-h-0 flex-1 overflow-y-auto p-4">
                {!page.human_verification?.required && page.screenshot && (
                  <div className="mb-3 rounded-lg border border-cyan-400/20 bg-black p-2">
                    <div className="mb-2 flex items-center justify-between"><span className="font-mono-tech text-[9px] tracking-widest text-cyan-200">LIVE LOGIN BROWSER</span><span className="text-[9px] text-zinc-600">Click the browser yourself</span></div>
                    <img src={page.screenshot} alt="Live KZ browser login view" onPointerUp={(event) => { event.preventDefault(); void clickLiveBrowser(event); }} onWheel={queueBrowserScroll} draggable={false} style={{ touchAction: "none", userSelect: "none" }} className="block h-auto w-full cursor-pointer select-none" />
                    <p className="mt-2 text-[10px] leading-relaxed text-zinc-600">Scroll and click inside this live browser yourself. You can move through the full login page, then enter your credentials in the visible controls. KZ does not auto-login or treat human verification as account login.</p>
                  </div>
                )}

                {page.human_verification?.required && (
                  <div className="mb-3 rounded-lg border border-amber-400/30 bg-amber-400/5 p-3">
                    <div className="font-mono-tech text-[10px] tracking-widest text-amber-200">HUMAN VERIFICATION REQUIRED</div>
                    <p className="mt-1 text-xs leading-relaxed text-amber-100/80">{page.human_verification.message || "Complete the challenge yourself. KZ will not bypass it."}</p>
                    <p className="mt-2 text-[10px] leading-relaxed text-amber-100/60">The server browser is shown below. Complete the challenge yourself exactly as Fiverr asks. KZ forwards only your manual press/hold input; it does not solve or bypass the challenge.</p>
                    {page.screenshot && (
                      <div className="mt-3 overflow-hidden rounded-lg border border-amber-400/20 bg-black">
                        <img
                          src={page.screenshot}
                          alt="Live KZ browser view for manual human verification"
                          onPointerDown={beginHumanPress}
                          onWheel={queueBrowserScroll}
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
                      <button onClick={checkHumanVerification} disabled={busy || challengeBusy} className="rounded-lg border border-amber-400/30 bg-amber-400/10 py-2 font-mono-tech text-[9px] tracking-widest text-amber-100 disabled:opacity-40">{challengeBusy ? "CHECKING..." : "CHECK VERIFICATION"}</button>
                      <button onClick={refresh} disabled={busy || challengeBusy} className="rounded-lg border border-amber-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-amber-200 disabled:opacity-40">REFRESH VIEW</button>
                    </div>
                  </div>
                )}

                {status !== "connected" && !page.human_verification?.required && (
                  <div className="space-y-2">
                    <button onClick={refresh} disabled={busy} className="w-full rounded-lg border border-cyan-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-200 disabled:opacity-40">{busy ? "CHECKING LIVE SESSION..." : "VERIFY LOGIN"}</button>
                    <button onClick={confirmConnection} disabled={busy || status !== "ready_to_confirm"} className="w-full rounded-lg border border-cyan-400/30 bg-cyan-400/10 py-3 font-mono-tech text-[10px] tracking-widest text-cyan-100 disabled:opacity-40">
                      {status === "login_required" ? "LOGIN REQUIRED" : status === "ready_to_confirm" ? "LOGIN VERIFIED — CONNECT ACCOUNT" : "CHECKING LOGIN..."}
                    </button>
                    <p className="text-[10px] leading-relaxed text-zinc-600">KZ will never display CONNECTED merely because this website opened. The live browser must first show authenticated evidence.</p>
                  </div>
                )}

                {status === "connected" && (
                  <div className="rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-3">
                    <div className="font-mono-tech text-[10px] tracking-widest text-cyan-200">ACCOUNT READY</div>
                    <p className="mt-1 text-xs text-zinc-500">Give KZ the task you want performed inside this account.</p>
                    <textarea value={task} onChange={(e) => setTask(e.target.value)} placeholder="Example: Find the best matching opportunity and prepare the application. Do not submit until I approve." className="mt-3 min-h-24 w-full rounded-lg border border-white/10 bg-black/20 p-3 text-sm text-white outline-none" />
                    <button onClick={createTask} disabled={busy || !task.trim()} className="mt-2 w-full rounded-lg border border-cyan-400/25 bg-cyan-400/10 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-100 disabled:opacity-40">{busy ? "PREPARING..." : "PLAN TASK"}</button>
                    {workflow && <div className="mt-3 rounded-lg border border-white/5 p-3 text-xs text-zinc-400"><div>Workflow: <span className="text-cyan-200">{workflow.id}</span></div><div className="mt-1">Status: <span className="text-cyan-200">{workflow.status}</span></div>{workflow.status === "waiting_for_approval" && <div className="mt-2 text-amber-200">Open the approval queue to approve or reject the consequential action.</div>}</div>}
                  </div>
                )}

                <div className="mt-3 rounded-lg border border-white/5 bg-white/[0.02] p-3"><div className="truncate text-xs text-cyan-200">{page.title || "Connected page"}</div><div className="mt-1 break-all text-[9px] text-zinc-600">{page.url}</div></div>

                <div className="mt-3 space-y-2">
                  {(page.buttons || []).filter((x) => x.text).map((x, i) => <button key={"b" + i} onClick={() => setSelector(x.selector || "__text__:" + x.text)} className={"block w-full rounded-lg border p-2 text-left text-xs " + (selector === x.selector ? "border-amber-400/40 bg-amber-400/10 text-amber-100" : "border-white/5 text-zinc-500")}>BUTTON · {x.text}</button>)}
                  {(page.inputs || []).map((x, i) => <button key={i} onClick={() => setSelector(x.selector)} className={"block w-full rounded-lg border p-2 text-left text-xs " + (selector === x.selector ? "border-cyan-400/40 bg-cyan-400/10 text-cyan-100" : "border-white/5 text-zinc-500")}>{x.type} · {x.name || x.placeholder || x.selector}</button>)}
                </div>

                {selector && <div className="mt-3 rounded-lg border border-cyan-400/15 p-3"><div className="font-mono-tech text-[9px] tracking-widest text-cyan-300">BROWSER FIELD</div><div className="mt-1 text-[10px] text-zinc-600">The value is sent only to the current browser action; KZ does not write it to memory.</div><input value={value} onChange={(e) => setValue(e.target.value)} type={page.inputs?.find((x) => x.selector === selector)?.type === "password" ? "password" : "text"} placeholder="Enter value" className="mt-2 w-full rounded-lg border border-white/10 bg-black/20 p-2 text-sm text-white" autoComplete="off" /><button onClick={() => action("fill")} disabled={busy} className="mt-2 w-full rounded-lg border border-cyan-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-cyan-200">FILL CURRENT FIELD</button></div>}

                <div className="mt-3 flex gap-2"><button onClick={refresh} disabled={busy} className="flex-1 rounded-lg border border-white/10 py-2 font-mono-tech text-[9px] tracking-widest text-zinc-400">REFRESH</button><button onClick={() => action("click")} disabled={busy || !selector} className="flex-1 rounded-lg border border-amber-400/20 py-2 font-mono-tech text-[9px] tracking-widest text-amber-200">CLICK SELECTED</button></div>

                <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border border-white/5 bg-black/20 p-3 text-[10px] text-zinc-500">{page.text || ""}</pre>
              </div>
            )}
          </aside>
        </>
      )}
    </>
  );
}
