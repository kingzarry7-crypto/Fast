"use client";

type CoreState = "idle" | "thinking" | "speaking" | "listening" | "error";

const stateColors: Record<CoreState, string> = {
  idle: "#00f0ff",
  thinking: "#8b5cf6",
  speaking: "#10b981",
  listening: "#f59e0b",
  error: "#ef4444",
};

const stateLabels: Record<CoreState, string> = {
  idle: "READY",
  thinking: "THINKING",
  speaking: "RESPONDING",
  listening: "LISTENING",
  error: "ERROR",
};

export default function AICore({
  state = "idle",
  size = 220,
}: {
  state?: CoreState;
  size?: number;
}) {
  const color = stateColors[state];
  const active = state !== "idle";

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {/* Outer pulsing rings when active */}
      {active && (
        <>
          <span
            className="kz-core-ring absolute inset-0 rounded-full"
            style={{ border: `1px solid ${color}` }}
          />
          <span
            className="kz-core-ring absolute inset-0 rounded-full"
            style={{ border: `1px solid ${color}`, animationDelay: "0.8s" }}
          />
        </>
      )}

      {/* Slow-rotating outer dashed ring */}
      <span
        className="kz-core-rotate absolute rounded-full"
        style={{
          inset: size * 0.02,
          border: `1px dashed ${color}33`,
        }}
      />

      {/* Counter-rotating middle ring */}
      <span
        className="kz-core-rotate-reverse absolute rounded-full"
        style={{
          inset: size * 0.1,
          border: `1px solid ${color}55`,
          boxShadow: `0 0 24px ${color}22, inset 0 0 24px ${color}11`,
        }}
      />

      {/* Orbiting dot */}
      <span
        className="kz-orbit absolute rounded-full"
        style={{
          inset: size * 0.06,
          animationDuration: active ? "3s" : "12s",
        }}
      >
        <span
          className="absolute rounded-full"
          style={{
            width: size * 0.028,
            height: size * 0.028,
            background: color,
            boxShadow: `0 0 12px ${color}, 0 0 24px ${color}`,
            top: 0,
            left: "50%",
            transform: "translateX(-50%)",
          }}
        />
      </span>

      {/* Inner glow halo */}
      <div
        className="kz-core-pulse absolute rounded-full"
        style={{
          inset: size * 0.2,
          background: `radial-gradient(circle, ${color}44 0%, ${color}11 40%, transparent 70%)`,
          boxShadow: `0 0 60px ${color}55, inset 0 0 40px ${color}33`,
        }}
      />

      {/* Mid detail ring */}
      <div
        className="absolute rounded-full"
        style={{
          inset: size * 0.28,
          border: `1px solid ${color}77`,
          opacity: 0.6,
        }}
      />

      {/* Solid core */}
      <div
        className="relative rounded-full"
        style={{
          width: size * 0.3,
          height: size * 0.3,
          background: `radial-gradient(circle at 35% 35%, #ffffff 0%, ${color} 40%, ${color}88 100%)`,
          boxShadow: `0 0 40px ${color}, 0 0 80px ${color}88, inset 0 0 20px #ffffff44`,
        }}
      />

      {/* Center bright dot */}
      <div
        className="absolute rounded-full"
        style={{
          width: size * 0.06,
          height: size * 0.06,
          background: "#ffffff",
          boxShadow: `0 0 20px #ffffff, 0 0 40px ${color}`,
        }}
      />

      {/* Status label */}
      <div className="absolute -bottom-8 left-1/2 -translate-x-1/2">
        <span
          className="font-mono-tech text-[10px] tracking-[0.4em] uppercase"
          style={{ color, textShadow: `0 0 10px ${color}88` }}
        >
          {stateLabels[state]}
        </span>
      </div>
    </div>
  );
}
