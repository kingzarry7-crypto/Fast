"use client";

/** Cyan robot head mark — replaces "KZ" text logo */
export default function RobotHead({
  size = 36,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  const id = "kzRobot";
  return (
    <div
      className={
        "relative shrink-0 rounded-xl border border-cyan-400/50 bg-[#020b18] flex items-center justify-center overflow-hidden shadow-[0_0_16px_rgba(0,240,255,0.35)] " +
        className
      }
      style={{ width: size, height: size }}
      aria-label="King Zarry robot"
    >
      <span className="absolute inset-0 rounded-xl border border-cyan-300/20 animate-pulse pointer-events-none" />
      <svg viewBox="0 0 100 100" className="relative z-10 h-[85%] w-[85%]" role="img">
        <defs>
          <linearGradient id={id + "Shell"} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#f1ffff" />
            <stop offset="40%" stopColor="#8cecff" />
            <stop offset="75%" stopColor="#12bfe8" />
            <stop offset="100%" stopColor="#063247" />
          </linearGradient>
          <filter id={id + "Glow"}>
            <feGaussianBlur stdDeviation="1.4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <path d="M50 8v10" stroke="#00f0ff" strokeWidth="3" strokeLinecap="round" />
        <circle cx="50" cy="7" r="3.5" fill="#00f0ff" filter={`url(#${id}Glow)`} />
        <rect
          x="22"
          y="22"
          width="56"
          height="52"
          rx="14"
          fill={`url(#${id}Shell)`}
          stroke="#00dfff"
          strokeWidth="2"
        />
        <path
          d="M30 38 Q50 28 70 38 v26 q-20 12 -40 0 z"
          fill="#020b15"
          stroke="#00dfff"
          strokeWidth="1.6"
        />
        <path d="M36 48h9" stroke="#f3ffff" strokeWidth="5" strokeLinecap="round" />
        <path d="M55 48h9" stroke="#f3ffff" strokeWidth="5" strokeLinecap="round" />
        <path
          d="M39 58 q11 8 22 0"
          fill="none"
          stroke="#00f0ff"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
        <rect x="14" y="40" width="8" height="16" rx="3" fill="#0a3a4a" stroke="#00dfff" strokeWidth="1.5" />
        <rect x="78" y="40" width="8" height="16" rx="3" fill="#0a3a4a" stroke="#00dfff" strokeWidth="1.5" />
      </svg>
    </div>
  );
}
