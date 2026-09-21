"use client";

export default function HeroRings({
  size = 640,
  color = "#00f0ff",
}: {
  size?: number;
  color?: string;
}) {
  return (
    <div
      className="absolute inset-0 flex items-center justify-center pointer-events-none"
      aria-hidden="true"
    >
      <div
        className="relative"
        style={{ width: size, height: size }}
      >
        {/* Concentric breathing rings */}
        {[1.0, 0.82, 0.64, 0.46].map((scale, i) => (
          <div
            key={i}
            className="kz-ring-breathe absolute inset-0 rounded-full"
            style={{
              transform: `scale(${scale})`,
              border: `1px solid ${color}${i === 0 ? "55" : i === 1 ? "44" : i === 2 ? "33" : "22"}`,
              boxShadow: i === 0 ? `0 0 60px ${color}33, inset 0 0 60px ${color}22` : undefined,
              animationDelay: `${i * 0.4}s`,
            }}
          />
        ))}

        {/* Rotating dashed guide */}
        <div
          className="kz-core-rotate absolute rounded-full"
          style={{
            inset: "6%",
            border: `1px dashed ${color}33`,
          }}
        />

        {/* Counter-rotating tick ring */}
        <div
          className="kz-core-rotate-reverse absolute rounded-full"
          style={{
            inset: "18%",
            border: `1px dashed ${color}22`,
          }}
        />

        {/* Corner data nodes */}
        {[0, 90, 180, 270].map((angle) => (
          <div
            key={angle}
            className="absolute rounded-full"
            style={{
              width: 8,
              height: 8,
              background: color,
              boxShadow: `0 0 16px ${color}, 0 0 32px ${color}`,
              top: "50%",
              left: "50%",
              transform: `translate(-50%, -50%) rotate(${angle}deg) translateY(-${size / 2 - 12}px)`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
