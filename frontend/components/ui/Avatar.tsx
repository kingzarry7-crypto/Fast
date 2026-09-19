"use client";

import React, { useMemo, useState } from "react";

export type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl" | "2xl" | number;
export type AvatarVariant = "default" | "glass" | "holographic" | "minimal";
export type AvatarStatus = "online" | "offline" | "busy" | "away" | "idle" | null;

export interface AvatarProps {
  src?: string | null;
  alt?: string;
  name?: string | null;
  size?: AvatarSize;
  variant?: AvatarVariant;
  status?: AvatarStatus;
  online?: boolean | null;
  isAI?: boolean;
  fallback?: React.ReactNode | string | null;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
  showBorder?: boolean;
  aiLabel?: string;
}

function getInitials(name?: string | null): string {
  if (!name) return "";
  const cleaned = name.trim();
  if (!cleaned) return "";
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
  const first = parts[0].charAt(0).toUpperCase();
  const last = parts[parts.length - 1].charAt(0).toUpperCase();
  return first === last? first : `${first}${last}`.slice(0, 2);
}

function sizeToClasses(size: AvatarSize) {
  if (typeof size === "number") return { wrapper: "w-10 h-10", text: "text-[13px]", status: "w-3 h-3", px: size };
  switch (size) {
    case "xs": return { wrapper: "w-7 h-7", text: "text-[11px]", status: "w-2 h-2", px: 28 };
    case "sm": return { wrapper: "w-8 h-8", text: "text-[11px]", status: "w-2.5 h-2.5", px: 32 };
    case "md": return { wrapper: "w-10 h-10", text: "text-[12px]", status: "w-3 h-3", px: 40 };
    case "lg": return { wrapper: "w-12 h-12", text: "text-[13px]", status: "w-3.5 h-3.5", px: 48 };
    case "xl": return { wrapper: "w-16 h-16", text: "text-[15px]", status: "w-4 h-4", px: 64 };
    case "2xl": return { wrapper: "w-20 h-20", text: "text-[18px]", status: "w-4 h-4", px: 80 };
    default: return { wrapper: "w-10 h-10", text: "text-[12px]", status: "w-3 h-3", px: 40 };
  }
}

function statusConfig(status: AvatarStatus, online?: boolean | null) {
  if (typeof online === "boolean") status = online? "online" : "offline";
  if (!status) return null;
  const map: Record<string, { color: string; ring: string; label: string }> = {
    online: { color: "bg-emerald-400", ring: "ring-emerald-400/20 shadow-[0_0_8px_rgba(16,185,129,0.5)]", label: "Online" },
    offline: { color: "bg-white/30", ring: "ring-white/10", label: "Offline" },
    busy: { color: "bg-rose-400", ring: "ring-rose-400/20 shadow-[0_0_8px_rgba(251,113,133,0.4)]", label: "Busy" },
    away: { color: "bg-amber-300", ring: "ring-amber-300/20", label: "Away" },
    idle: { color: "bg-white/25", ring: "ring-white/10", label: "Idle" },
  };
  return map[status] || null;
}

export default function Avatar({ src, alt, name, size = "md", variant = "default", status = null, online = null, isAI = false, fallback, className = "", onClick, disabled = false, showBorder = true, aiLabel = "KING ZARRY AI" }: AvatarProps) {
  const [imgError, setImgError] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const { wrapper, text, status: statusSize } = sizeToClasses(size);
  const initials = useMemo(() => getInitials(name), [name]);
  const statusInfo = useMemo(() => statusConfig(status, online), [status, online]);
  const hasImage =!!src &&!imgError;
  const altText = alt || (isAI? aiLabel : name? `${name} avatar` : "Avatar");
  const variantStyles = useMemo(() => {
    switch (variant) {
      case "glass": return "bg-white/[0.04] backdrop-blur-xl border-white/[0.08] shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_8px_24px_rgba(0,0,0,0.4)]";
      case "holographic": return "bg-gradient-to-b from-[#0F1A2E] to-[#0A0F1E] border-cyan-300/20 shadow-[0_0_20px_rgba(34,211,238,0.15),inset_0_1px_0_rgba(255,255,255,0.08)]";
      case "minimal": return "bg-[#0E131D] border-white/[0.06] shadow-none";
      default: return "bg-gradient-to-b from-[#141C2E] to-[#0B0F1A] border-white/[0.08] shadow-[0_8px_24px_rgba(0,0,0,0.45),inset_0_1px_0_rgba(255,255,255,0.06)]";
    }
  }, [variant]);
  const isInteractive =!!onClick &&!disabled;
  const Tag: any = isInteractive? "button" : "div";
  const customStyle: React.CSSProperties | undefined = typeof size === "number"? { width: size, height: size } : undefined;

  return (
    <div className={`relative inline-flex shrink-0 ${className}`}>
      {isAI && variant!== "minimal" && <span aria-hidden="true" className="pointer-events-none absolute -inset-[2px] rounded-full bg-gradient-to-b from-cyan-300/20 via-cyan-300/5 to-violet-400/20 blur-[0.5px] opacity-70 hidden md:block" />}
      <Tag
        onClick={isInteractive? onClick : undefined}
        disabled={isInteractive? disabled : undefined}
        aria-label={isInteractive? (isAI? `Open ${aiLabel}` : name? `Open ${name}` : "Open profile") : undefined}
        className={`relative ${typeof size === "number"? "" : wrapper} rounded-full overflow-hidden flex items-center justify-center select-none ${showBorder? "border" : "border-0"} ${variantStyles} ${isInteractive? "cursor-pointer hover:border-white/[0.14] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/30 active:scale-[0.98] transition-all" : ""} ${disabled? "opacity-60 pointer-events-none" : ""}`}
        style={customStyle}
      >
        <span aria-hidden="true" className="pointer-events-none absolute inset-0 rounded-full bg-[radial-gradient(120px_80px_at_30%_20%,rgba(255,255,255,0.08),transparent)]" />
        {hasImage && <img src={src as string} alt={altText} className={`w-full h-full object-cover rounded-full ${loaded? "opacity-100" : "opacity-0"} transition-opacity duration-300`} onLoad={() => setLoaded(true)} onError={() => setImgError(true)} loading="lazy" />}
        {hasImage &&!loaded && <span aria-hidden="true" className="absolute inset-0 bg-white/[0.04] animate-pulse" />}
        {!hasImage && (
          <span className={`relative z-[1] font-semibold tracking-[-0.01em] ${text} ${isAI? "text-cyan-100/90" : "text-white/80"}`}>
            {fallback? (typeof fallback === "string"? fallback.slice(0,2).toUpperCase() : fallback) : initials? initials : isAI? <span className="relative w-[1.1em] h-[1.1em] flex items-center justify-center"><span aria-hidden="true" className="absolute inset-0 rounded-full bg-cyan-400/[0.12] border border-cyan-300/20" /><span aria-hidden="true" className="w-[4px] h-[4px] rounded-full bg-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.8)]" /></span> : <span className="text-white/40">•</span>}
          </span>
        )}
        {isAI &&!hasImage && <span aria-hidden="true" className="pointer-events-none absolute inset-0 rounded-full bg-[radial-gradient(80px_60px_at_50%_45%,rgba(34,211,238,0.14),transparent_70%)]" />}
      </Tag>
      {statusInfo && <span className={`absolute -bottom-0.5 -right-0.5 ${statusSize} rounded-full border-[2px] border-[#080B14] ${statusInfo.color} ${statusInfo.ring}`} aria-label={statusInfo.label} />}
    </div>
  );
}
