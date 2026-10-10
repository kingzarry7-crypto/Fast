"use client";

import AICore from "@/components/AICore";

/**
 * Compact animated avatar used anywhere the assistant's former static head appeared.
 * It reuses the same AICore portrait, aura, rings, scan sweep and state styling.
 */
export default function RobotHead({
  size = 36,
  className = "",
  state = "idle",
}: {
  size?: number;
  className?: string;
  state?: "idle" | "thinking" | "speaking" | "listening" | "error";
}) {
  return (
    <div
      className={"relative flex shrink-0 items-center justify-center overflow-hidden rounded-xl border border-cyan-400/50 bg-[#020b18] shadow-[0_0_16px_rgba(0,240,255,0.35)] " + className}
      style={{ width: size, height: size }}
      aria-label={`King Zarry AI animated core: ${state}`}
      role="img"
    >
      <AICore state={state} size={size} compact />
      <span className="pointer-events-none absolute inset-0 rounded-[inherit] border border-cyan-300/20" aria-hidden="true" />
    </div>
  );
}
