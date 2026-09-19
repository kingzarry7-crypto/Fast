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
  size = 160,
}: {
  state?: CoreState;
  size?: number;
}) {
  const color = stateColors[state];

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      {/* Outer pulse rings */}
      {state !== "idle" && (
        <>
          <span
            className="kz-core-ring absolute inset-0 rounded-full"
            style={{ border: `1px solid ${color}` }}
          />
          <span
            className="kz-core-ring absolute inset-0 rounded-full"
            style={{
              border: `1px solid ${color}`,
              animationDelay: "0.6s",
            }}
          />
        </>
      )}

      {/* Rotating ring */}
      <span
        className="kz-core-rotate absolute rounded-full"
        style={{
          inset: size * 0.08,
          border: `1px dashed ${color}44`,
        }}
      />

      {/* Core glow */}
      <div
        className="kz-core-pulse absolute rounded-full"
        style={{
          inset: size * 0.22,
          background: `radial-gradient(circle, ${color}33 0%, transparent 70%)`,
          boxShadow: `0 0 40px ${color}55`,
        }}
      />

      {/* Solid core */}
      <div
        className="relative rounded-full"
        style={{
          width: size * 0.28,
          height: size * 0.28,
          background: `radial-gradient(circle at 35% 35%, #ffffff, ${color})`,
          boxShadow: `0 0 30px ${color}, 0 0 60px ${color}66`,
        }}
      />

      {/* State label */}
      <div className="absolute -bottom-6 left-1/2 -translate-x-1/2">
        <span
          className="font-mono text-[10px] tracking-[0.3em] uppercase"
          style={{ color }}
        >
          {stateLabels[state]}
        </span>
      </div>
    </div>
  );
}
