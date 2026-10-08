"use client";

type VoiceCallUIProps = {
  status: string;
  prompt?: string;
  elapsed: number;
  muted: boolean;
  speaking: boolean;
  listening: boolean;
  onMute: () => void;
  onEnd: () => void;
  onStopSpeaking: () => void;
};

function formatTime(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60).toString().padStart(2, "0");
  const seconds = (totalSeconds % 60).toString().padStart(2, "0");
  return minutes + ":" + seconds;
}

export default function VoiceCallUI({
  status,
  prompt,
  elapsed,
  muted,
  speaking,
  listening,
  onMute,
  onEnd,
  onStopSpeaking,
}: VoiceCallUIProps) {
  const title =
    status === "MIC MUTED"
      ? "Microphone muted"
      : status === "SPEAKING"
        ? "King Zarry is speaking"
        : status === "THINKING..."
          ? "Thinking..."
          : "Listening...";

  return (
    <div className="fixed inset-0 z-[100] overflow-hidden bg-[#14182f] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_42%,rgba(26,211,255,0.16),transparent_28%),radial-gradient(circle_at_50%_70%,rgba(83,58,190,0.16),transparent_42%)]" />
      <div
        className="absolute inset-0 opacity-30"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
        }}
      />

      <div className="relative z-[101] flex h-full min-h-0 flex-col" aria-label="King Zarry AI live voice call">
        <div className="flex items-center justify-between px-5 pt-[max(1.25rem,env(safe-area-inset-top))] sm:px-8">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-[0.28em] text-cyan-300/80">
              AI Assistance
            </p>
            <p className="mt-1 text-sm font-semibold tracking-wide text-white">
              King Zarry AI
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 backdrop-blur-md">
            <span
              className={
                "h-2 w-2 rounded-full animate-pulse " +
                (muted ? "bg-red-400" : speaking ? "bg-violet-300" : "bg-cyan-300")
              }
            />
            <span className="font-mono text-[10px] tracking-[0.2em] text-white/70">
              {status}
            </span>
          </div>
        </div>

        <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-5 pb-28 pt-8">
          <div className="relative flex h-[min(68vw,330px)] w-[min(68vw,330px)] max-h-[330px] max-w-[330px] items-center justify-center">
            <div
              className={
                "absolute inset-0 rounded-full border transition-all duration-500 " +
                (speaking
                  ? "scale-105 border-violet-300/70 shadow-[0_0_90px_rgba(167,139,250,.45)]"
                  : muted
                    ? "border-red-300/45 shadow-[0_0_60px_rgba(248,113,113,.22)]"
                    : "border-cyan-300/65 shadow-[0_0_90px_rgba(34,211,238,.38)]")
              }
            />
            <div
              className={
                "absolute inset-[5%] rounded-full border border-white/10 transition-transform duration-700 " +
                (listening ? "scale-[1.03]" : "scale-100")
              }
            />
            <div
              className={
                "absolute inset-[11%] rounded-full border border-cyan-300/20 " +
                (listening ? "animate-pulse" : "")
              }
            />

            <div
              className={
                "relative flex h-[72%] w-[72%] items-center justify-center overflow-hidden rounded-full border border-cyan-200/25 transition-all duration-500 " +
                (speaking
                  ? "bg-[radial-gradient(circle_at_35%_30%,rgba(196,181,253,.92),rgba(88,28,135,.58)_38%,rgba(8,22,48,.96)_72%)] shadow-[inset_0_0_55px_rgba(196,181,253,.22),0_0_70px_rgba(139,92,246,.35)]"
                  : "bg-[radial-gradient(circle_at_35%_30%,rgba(91,235,255,.82),rgba(7,84,112,.62)_38%,rgba(5,15,35,.97)_72%)] shadow-[inset_0_0_55px_rgba(34,211,238,.18),0_0_70px_rgba(34,211,238,.30)]")
              }
            >
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_60%_75%,transparent_20%,rgba(0,0,0,.28)_70%)]" />
              <svg
                viewBox="0 0 260 120"
                className={
                  "relative z-10 h-[44%] w-[78%] " +
                  (speaking || listening ? "animate-pulse" : "")
                }
                aria-hidden="true"
              >
                <path
                  d="M0 60 C18 60 18 60 30 60 C39 60 40 45 48 45 C56 45 56 75 64 75 C72 75 73 52 82 52 C91 52 91 68 100 68 C109 68 110 36 120 36 C130 36 130 83 140 83 C150 83 151 57 160 57 C169 57 169 70 178 70 C187 70 188 47 198 47 C208 47 208 62 220 62 C232 62 238 60 260 60"
                  fill="none"
                  stroke="rgba(194,245,255,.85)"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
                <path
                  d="M0 60 C25 60 27 60 38 60 C47 60 49 53 58 53 C67 53 69 66 77 66 C87 66 88 58 98 58 C108 58 111 72 120 72 C130 72 132 48 142 48 C152 48 153 66 163 66 C173 66 174 55 184 55 C194 55 198 63 208 63 C220 63 230 60 260 60"
                  fill="none"
                  stroke="rgba(34,211,238,.65)"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              </svg>
            </div>
          </div>

          <div className="mt-8 w-full max-w-md text-center">
            <p className="text-2xl font-light tracking-tight text-white">{title}</p>
            <p className="mt-2 min-h-5 truncate px-4 text-xs text-cyan-100/45">
              {prompt || "Speak naturally — King Zarry AI is listening."}
            </p>
            <p className="mt-3 font-mono text-[10px] tracking-[0.25em] text-white/40">
              {formatTime(elapsed)}
            </p>
          </div>
        </div>

        <div className="absolute bottom-0 left-0 right-0 z-[110] px-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
          <div className="mx-auto flex max-w-md items-center justify-center gap-5">
            <button
              type="button"
              onClick={onMute}
              aria-label={muted ? "Unmute microphone" : "Mute microphone"}
              className={
                "flex h-16 w-16 items-center justify-center rounded-full border backdrop-blur-md transition-all active:scale-95 " +
                (muted
                  ? "border-red-300/60 bg-red-500/25 text-red-100 shadow-[0_0_30px_rgba(248,113,113,.22)]"
                  : "border-white/15 bg-white/10 text-white hover:bg-white/15")
              }
            >
              {muted ? (
                <span className="text-xl">🔇</span>
              ) : (
                <svg width="23" height="23" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <rect x="7" y="3" width="10" height="13" rx="5" stroke="currentColor" strokeWidth="1.8" />
                  <path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
              )}
            </button>

            <button
              type="button"
              onClick={onEnd}
              aria-label="End AI voice call"
              className="flex h-16 w-16 items-center justify-center rounded-full border border-red-300/50 bg-red-500/90 text-white shadow-[0_0_35px_rgba(248,113,113,.28)] transition-all hover:bg-red-500 active:scale-95"
            >
              <svg width="25" height="25" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M7.2 4.8 9.5 3.7c.7-.3 1.5 0 1.8.7l1.1 2.7c.2.5.1 1.1-.3 1.5l-1.4 1.2a13.2 13.2 0 0 0 3.5 3.5l1.2-1.4c.4-.4 1-.5 1.5-.3l2.7 1.1c.7.3 1 1.1.7 1.8l-1.1 2.3c-.3.7-1 1.1-1.7 1.1C10.1 17.9 6.1 13.9 6.1 7c0-.7.4-1.4 1.1-1.7Z" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>

            <button
              type="button"
              onClick={onStopSpeaking}
              disabled={!speaking}
              aria-label="Stop AI speech"
              className="flex h-16 w-16 items-center justify-center rounded-full border border-white/15 bg-white/10 text-white transition-all hover:bg-white/15 disabled:cursor-default disabled:opacity-40 active:scale-95"
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M4 10v4M8 7v10M12 5v14M16 7v10M20 10v4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </button>
          </div>
          <p className="mt-3 text-center font-mono text-[9px] tracking-[0.22em] text-white/30">
            LIVE VOICE • SECURE SESSION
          </p>
        </div>
      </div>
    </div>
  );
}
