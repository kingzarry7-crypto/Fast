"use client";

/** Shared portrait avatar: always use the uploaded human-style core image, never a robot illustration. */
export default function RobotHead({ size = 36, className = "" }: { size?: number; className?: string }) {
  return (
    <div
      className={"relative shrink-0 rounded-xl border border-cyan-400/50 bg-[#020b18] flex items-center justify-center overflow-hidden shadow-[0_0_16px_rgba(0,240,255,0.35)] " + className}
      style={{ width: size, height: size }}
      aria-label="King Zarry AI human profile"
    >
      <img
        src="/human-ai-core.webp"
        alt="King Zarry AI human profile"
        className="relative z-10 h-full w-full object-contain object-center"
        draggable={false}
      />
      <span className="absolute inset-0 rounded-xl border border-cyan-300/20 pointer-events-none" aria-hidden="true" />
    </div>
  );
}
