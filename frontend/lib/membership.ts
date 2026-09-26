/**
 * Frontend membership helpers.
 * Server is_subscribed from /api/auth/me is preferred; localStorage is fallback.
 */

export const FREE_DAILY_MESSAGE_LIMIT = 25;

const VIP_KEY = "kz_web_vip";
const VIP_PLAN_KEY = "kz_web_vip_plan";
const VIP_SINCE_KEY = "kz_web_vip_since";

function dayKey(userId?: string | null): string {
  const day = new Date().toISOString().slice(0, 10);
  return `kz_free_msgs_${userId || "anon"}_${day}`;
}

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

export interface MembershipSnapshot {
  isVip: boolean;
  plan: string | null;
  since: string | null;
  freeMessagesUsedToday: number;
  freeMessagesRemaining: number;
  freeDailyLimit: number;
}

export function getIsVip(): boolean {
  if (!canUseStorage()) return false;
  return localStorage.getItem(VIP_KEY) === "1";
}

export function getVipPlan(): string | null {
  if (!canUseStorage()) return null;
  return localStorage.getItem(VIP_PLAN_KEY);
}

export function setVipLocal(plan?: string | null): void {
  if (!canUseStorage()) return;
  localStorage.setItem(VIP_KEY, "1");
  if (plan) localStorage.setItem(VIP_PLAN_KEY, plan);
  if (!localStorage.getItem(VIP_SINCE_KEY)) {
    localStorage.setItem(VIP_SINCE_KEY, new Date().toISOString());
  }
  window.dispatchEvent(new Event("kz-membership-change"));
}

export function clearVipLocal(): void {
  if (!canUseStorage()) return;
  localStorage.removeItem(VIP_KEY);
  localStorage.removeItem(VIP_PLAN_KEY);
  localStorage.removeItem(VIP_SINCE_KEY);
  window.dispatchEvent(new Event("kz-membership-change"));
}

export function getFreeMessageCount(userId?: string | null): number {
  if (!canUseStorage()) return 0;
  return Number(localStorage.getItem(dayKey(userId)) || "0");
}

export function incrementFreeMessageCount(userId?: string | null): number {
  if (!canUseStorage()) return 0;
  const next = getFreeMessageCount(userId) + 1;
  localStorage.setItem(dayKey(userId), String(next));
  return next;
}

export function getMembershipSnapshot(userId?: string | null): MembershipSnapshot {
  const used = getFreeMessageCount(userId);
  const isVip = getIsVip();
  return {
    isVip,
    plan: getVipPlan(),
    since: canUseStorage() ? localStorage.getItem(VIP_SINCE_KEY) : null,
    freeMessagesUsedToday: used,
    freeMessagesRemaining: Math.max(0, FREE_DAILY_MESSAGE_LIMIT - used),
    freeDailyLimit: FREE_DAILY_MESSAGE_LIMIT,
  };
}

export function getTelegramBotUrl(): string {
  if (typeof process !== "undefined" && process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL) {
    return process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL;
  }
  return "https://t.me/KingZarryAIBot";
}

export function getTelegramVipStartUrl(): string {
  const base = getTelegramBotUrl().replace(/\/$/, "");
  if (base.includes("?")) return `${base}&start=vip`;
  return `${base}?start=vip`;
}

export function isVipFromUser(user?: { is_subscribed?: boolean } | null): boolean {
  if (user?.is_subscribed) return true;
  return getIsVip();
}
