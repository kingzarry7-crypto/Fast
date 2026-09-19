import React from "react";

export interface PageContainerProps {
  children: React.ReactNode;
  className?: string;
  size?: "sm" | "md" | "lg" | "xl" | "full";
  fullWidth?: boolean;
  centered?: boolean;
  padding?: boolean;
}

export function PageContainer({
  children,
  className = "",
  size = "xl",
  fullWidth = false,
  centered = false,
  padding = true,
}: PageContainerProps) {
  // Determine maximum width class based on size prop
  let maxWidthClass = "max-w-7xl";
  if (size === "sm") maxWidthClass = "max-w-3xl";
  else if (size === "md") maxWidthClass = "max-w-4xl";
  else if (size === "lg") maxWidthClass = "max-w-5xl";
  else if (size === "xl") maxWidthClass = "max-w-7xl";
  else if (size === "full" || fullWidth) maxWidthClass = "max-w-full";

  const paddingClass = padding ? "px-4 sm:px-6 md:px-8 py-6 md:py-8" : "";

  return (
    <div
      className={`relative min-h-[calc(100vh-4rem)] w-full flex flex-col bg-[#030712] text-slate-100 overflow-x-hidden selection:bg-cyan-500/30 selection:text-cyan-200 ${className}`}
    >
      {/* Cinematic Ambient Background Depth & Holographic Grid Atmosphere */}
      <div
        className="absolute inset-0 pointer-events-none z-0 overflow-hidden"
        aria-hidden="true"
      >
        {/* Soft radial primary cyan glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[350px] bg-gradient-to-b from-cyan-600/10 via-cyan-950/5 to-transparent rounded-full blur-3xl opacity-60" />

        {/* Restrained secondary purple highlight */}
        <div className="absolute top-1/3 right-[-10%] w-[500px] h-[500px] bg-purple-950/10 rounded-full blur-3xl opacity-40" />

        {/* Faint subtle grid pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#06b6d40a_1px,transparent_1px),linear-gradient(to_bottom,#06b6d40a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-30" />

        {/* Subtle horizontal scanline accent */}
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,transparent_98%,rgba(6,182,212,0.03)_100%)] bg-[size:100%_4px] pointer-events-none" />
      </div>

      {/* Main Content Viewport Frame */}
      <div
        className={`relative z-10 w-full mx-auto flex flex-col flex-1 ${maxWidthClass} ${paddingClass} ${
          centered ? "items-center text-center" : ""
        }`}
      >
        {children}
      </div>
    </div>
  );
}
