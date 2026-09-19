// Fast/frontend/lib/constants.ts
// Central constants for KING ZARRY AI web frontend.
// No side effects, no React, no secrets.


// -----------------------------------------------------------------------------
// Application
// -----------------------------------------------------------------------------

export const APP_NAME = "KING ZARRY AI" as const;

export const APP_SHORT_NAME = "KING ZARRY" as const;

export const APP_DESCRIPTION =
  "Your personal AI intelligence system." as const;

export const APP_TAGLINE =
  "Intelligence for the market." as const;


// -----------------------------------------------------------------------------
// Routes
// -----------------------------------------------------------------------------

export const ROUTES = {
  home: "/",
  alerts: "/alerts",
  chat: "/chat",
  dashboard: "/dashboard",
  history: "/history",
  login: "/login",
  markets: "/markets",
  news: "/news",
  pricing: "/pricing",
  settings: "/settings",
  signals: "/signals",
} as const;

export type AppRoute =
  (typeof ROUTES)[keyof typeof ROUTES];


// -----------------------------------------------------------------------------
// Navigation
// -----------------------------------------------------------------------------

export interface NavigationItem {
  label: string;
  href: string;
  section?: string;
}

export const MAIN_NAVIGATION: readonly NavigationItem[] = [
  {
    label: "Dashboard",
    href: ROUTES.dashboard,
    section: "main",
  },
  {
    label: "Chat",
    href: ROUTES.chat,
    section: "main",
  },
  {
    label: "Markets",
    href: ROUTES.markets,
    section: "intelligence",
  },
  {
    label: "Signals",
    href: ROUTES.signals,
    section: "intelligence",
  },
  {
    label: "News",
    href: ROUTES.news,
    section: "intelligence",
  },
  {
    label: "Alerts",
    href: ROUTES.alerts,
    section: "tools",
  },
  {
    label: "History",
    href: ROUTES.history,
    section: "tools",
  },
  {
    label: "Settings",
    href: ROUTES.settings,
    section: "account",
  },
] as const;

export const PUBLIC_NAVIGATION: readonly NavigationItem[] = [
  {
    label: "AI",
    href: "/#ai",
  },
  {
    label: "Markets",
    href: ROUTES.markets,
  },
  {
    label: "Signals",
    href: ROUTES.signals,
  },
  {
    label: "Pricing",
    href: ROUTES.pricing,
  },
] as const;


// -----------------------------------------------------------------------------
// Trading assets
// -----------------------------------------------------------------------------

export const SUPPORTED_ASSETS = [
  "BTC",
  "ETH",
  "SOL",
  "XAU/USD",
] as const;

export type SupportedAsset =
  (typeof SUPPORTED_ASSETS)[number];

export const SUPPORTED_ASSETS_DISPLAY = [
  "BTC",
  "ETH",
  "SOL",
  "XAU",
] as const;

export const SUPPORTED_SYMBOLS_MAP = {
  BTC: "BTC",
  ETH: "ETH",
  SOL: "SOL",
  "XAU/USD": "XAU/USD",
  XAUUSD: "XAU/USD",
  XAU: "XAU/USD",
} as const;

export type SupportedSymbolAlias =
  keyof typeof SUPPORTED_SYMBOLS_MAP;


// -----------------------------------------------------------------------------
// Trading timeframes
// -----------------------------------------------------------------------------

export const SUPPORTED_TIMEFRAMES = [
  "5M",
  "15M",
  "1H",
  "4H",
] as const;

export type SupportedTimeframe =
  (typeof SUPPORTED_TIMEFRAMES)[number];


// -----------------------------------------------------------------------------
// Subscription plans
// -----------------------------------------------------------------------------

export interface SubscriptionPlan {
  id: string;
  label: string;
  stars: number;
  days: number;
  interval: string;
}

export const SUBSCRIPTION_PLANS = {
  monthly: {
    id: "monthly",
    label: "Monthly",
    stars: 150,
    days: 30,
    interval: "30 days",
  },

  threeMonths: {
    id: "3months",
    label: "3 Months",
    stars: 500,
    days: 90,
    interval: "90 days",
  },

  yearly: {
    id: "yearly",
    label: "Yearly",
    stars: 2500,
    days: 365,
    interval: "365 days",
  },
} as const;

export const SUBSCRIPTION_PLANS_LIST: readonly SubscriptionPlan[] = [
  SUBSCRIPTION_PLANS.monthly,
  SUBSCRIPTION_PLANS.threeMonths,
  SUBSCRIPTION_PLANS.yearly,
] as const;


// -----------------------------------------------------------------------------
// Frontend limits
// -----------------------------------------------------------------------------

export const CHAT_MESSAGE_MIN_LENGTH = 1 as const;

export const CHAT_MESSAGE_MAX_LENGTH = 4000 as const;

export const PASSWORD_MIN_LENGTH = 8 as const;

export const PASSWORD_MAX_LENGTH = 128 as const;

export const USERNAME_MIN_LENGTH = 3 as const;

export const USERNAME_MAX_LENGTH = 100 as const;

export const DISPLAY_NAME_MAX_LENGTH = 255 as const;

export const USERNAME_REGEX =
  /^[a-z0-9_]{3,100}$/;


// -----------------------------------------------------------------------------
// Session configuration
// -----------------------------------------------------------------------------
//
// The frontend does not create, read, or manage this cookie.
// The browser and FastAPI manage the server session.

export const SESSION_DAYS_DEFAULT = 30 as const;


// -----------------------------------------------------------------------------
// Confirmed API paths
// -----------------------------------------------------------------------------
//
// These are paths only. Network requests remain centralized in lib/api.ts.

export const API_ENDPOINTS = {
  auth: {
    me: "/api/auth/me",
    login: "/api/auth/login",
    register: "/api/auth/register",
    logout: "/api/auth/logout",
  },

  chat: {
    send: "/api/chat",
  },

  health: "/health",

  root: "/",
} as const;


// -----------------------------------------------------------------------------
// Application metadata
// -----------------------------------------------------------------------------

export const APP_META = {
  name: APP_NAME,
  description: APP_DESCRIPTION,
  tagline: APP_TAGLINE,
} as const;
