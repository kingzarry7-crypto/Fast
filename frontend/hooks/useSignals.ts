Build and finish this file only:

Fast/frontend/hooks/useSignals.ts

You are working inside the existing KING ZARRY AI Next.js + TypeScript frontend.

FIRST: INSPECT THE PROJECT

Before writing code, inspect the existing project and determine the actual contracts already used by the frontend and backend.

Read:

* Fast/frontend/app/signals/page.tsx
* Fast/frontend/app/dashboard/page.tsx
* Fast/frontend/components/trading/SignalCard.tsx
* Fast/frontend/components/trading/TradeLevels.tsx
* Fast/frontend/components/trading/TradingChart.tsx
* Fast/frontend/components/trading/IndicatorPanel.tsx
* Fast/frontend/components/dashboard/RecentSignals.tsx
* Fast/frontend/hooks/useMarket.ts
* Fast/frontend/hooks/useChat.ts
* Fast/frontend/hooks/useAuth.ts
* Fast/frontend/lib/api.ts
* existing files under Fast/frontend/types/
* the actual FastAPI signal/trading endpoints in the repository

Do not guess an API endpoint, request body, response structure, signal field, or backend capability.

PURPOSE

Create a reusable useSignals() React hook for the KING ZARRY AI web frontend.

The hook should provide a clean interface for future and existing signal intelligence functionality.

It should manage, where actually supported by the existing backend:

* signal data
* selected symbol/asset
* selected timeframe
* loading state
* error state
* refresh
* request cancellation
* stale-request protection
* optional signal retrieval

Trading is only one capability of KING ZARRY AI. Do not design the hook as the entire AI system.

CRITICAL DATA RULE

NEVER fabricate trading signals.

Do not generate:

* fake BUY signals
* fake SELL signals
* fake WAIT signals
* fake entry prices
* fake stop losses
* fake take profits
* fake confidence percentages
* fake RSI
* fake EMA
* fake ATR
* fake market structure
* fake multi-timeframe analysis
* fake signal history
* fake timestamps
* fake outcomes
* fake win rates

Do not use:

Math.random()

Do not hardcode market values.

If a real signal endpoint does not currently exist, the hook must return an empty state rather than pretending signals are available.

TYPES

Use TypeScript.

Do not use any.

First reuse an existing signal type if one already exists in:

Fast/frontend/types/

or an existing trading component.

If no shared type exists, define a minimal local type based only on the actual backend response.

A reasonable shape, ONLY if it matches the existing project, could contain:

export interface SignalData {
  id?: string | number;
  symbol: string;
  timeframe?: string | null;
  direction?: string | null;
  status?: string | null;
  entry?: number | null;
  stop_loss?: number | null;
  take_profit_1?: number | null;
  take_profit_2?: number | null;
  take_profit_3?: number | null;
  confidence?: number | null;
  created_at?: string | null;
  timestamp?: string | null;
  [key: string]: unknown;
}

Do not add fields merely because they sound useful.

PUBLIC HOOK API

If the existing project does not already define a different interface, use a structure similar to:

export interface UseSignalsOptions {
  symbol?: string;
  timeframe?: string;
  autoLoad?: boolean;
}
export interface UseSignalsReturn {
  signals: SignalData[];
  isLoading: boolean;
  error: string | null;
  symbol: string;
  timeframe: string;
  refresh: () => Promise<void>;
  setSymbol: (symbol: string) => void;
  setTimeframe: (timeframe: string) => void;
}

Preserve an existing public interface if one already exists.

API CONNECTION

Only connect to an actual signal endpoint if one is confirmed in the repository.

Use:

NEXT_PUBLIC_API_BASE_URL

Do not search multiple guessed environment variables.

Do not dynamically import random API modules.

Do not guess routes such as:

/api/signals
/api/signal
/api/trading/signals
/api/market/signals

unless the repository confirms the exact route.

If no real endpoint exists yet:

* do not make a request
* return an empty signal array
* keep the hook API-ready
* do not fabricate a successful response

AUTHENTICATION

If the confirmed signal endpoint requires the logged-in web user:

credentials: "include"

must be used.

Do not store authentication tokens in:

* localStorage
* sessionStorage
* cookies manually from JavaScript

The existing authentication system uses the web session cookie.

Do not access Telegram authentication.

REQUEST SAFETY

Implement:

* AbortController
* request ID protection
* mounted-component protection
* safe cleanup
* prevention of stale responses overwriting newer results

If a user switches:

BTC → ETH

while a BTC request is still pending, an old BTC response must never overwrite the newer state.

Likewise for timeframe changes.

SYMBOL NORMALIZATION

Normalize symbol values consistently with the existing project.

For example:

BTC
ETH
SOL
XAU/USD

only if those exact values are already used by the project.

Do not silently change:

XAU/USD

into:

XAUUSDT

or another format unless the existing backend requires that exact transformation.

Preserve the backend’s actual symbol contract.

TIMEFRAME NORMALIZATION

Use the actual timeframe values already used by the project.

The current trading UI may use values such as:

5M
15M
1H
4H

but verify this in the repository first.

Do not invent additional timeframes.

REFRESH

refresh() should:

1. cancel any previous request if necessary
2. create a new request
3. request real signal data only if a confirmed endpoint exists
4. validate the response
5. update the signal state
6. handle errors
7. clean up safely

Do not silently replace a failed request with fake data.

SIGNAL VALIDATION

Validate important fields before exposing them to components.

For numeric fields:

* accept valid finite numbers
* convert numeric strings only when appropriate
* convert invalid numeric values to null

Do not silently convert invalid values into 0.

For direction/status:

* preserve the backend value
* do not invent a direction when one is missing

ERROR HANDLING

Handle:

* 401
* 403
* 404
* 422
* 429
* 500+
* network errors
* invalid JSON
* invalid response structure
* aborted requests

Use clear user-facing messages.

Do not expose:

* API keys
* tokens
* secrets
* passwords
* internal stack traces

Aborted or stale requests must not become visible error messages.

AUTO LOAD

If autoLoad exists:

* respect it
* do not introduce polling
* do not create background intervals
* do not repeatedly call the backend

Only fetch automatically when explicitly requested by the hook options.

NO SIGNAL ENGINE

This hook is not the place to invent or implement the trading strategy.

Do not calculate:

* EMA
* RSI
* ATR
* market structure
* trend
* confidence
* entry
* SL
* TP

unless the existing frontend architecture explicitly requires client-side calculations.

The actual signal engine should remain on the backend/AI layer.

The hook should retrieve and expose real signal data.

SIGNAL HISTORY

Do not invent signal history.

If the backend has a confirmed history endpoint and the existing UI needs it, implement it according to the actual API contract.

Otherwise keep history out of this hook.

WEB / TELEGRAM SEPARATION

This hook belongs to the web application.

Never import or access:

* Telegram bot modules
* Telegram SQLite databases
* Telegram subscriptions
* Telegram payment tables
* Telegram memory
* Telegram notification systems

The web app will use its own API and Neon-backed architecture.

UI SEPARATION

Do not create JSX.

Do not add Tailwind classes.

Do not add visual components.

The hook should only manage data/state.

The existing visual components handle the cinematic KING ZARRY AI interface.

PERFORMANCE

Keep the hook lightweight.

Do not introduce unnecessary dependencies.

Do not add polling.

Do not add WebSockets unless an existing project implementation already requires them.

Do not add timers unless explicitly required by an existing backend contract.

FILE SCOPE

Modify ONLY:

Fast/frontend/hooks/useSignals.ts

Do not modify:

* api.py
* database.py
* web_database.sql
* frontend/lib/api.ts
* useMarket.ts
* useAuth.ts
* useChat.ts
* pages
* components
* globals.css
* package.json

FINAL VERIFICATION

After implementing:

1. Run the frontend TypeScript/build check.
2. Fix all TypeScript errors caused by this file.
3. Confirm there is no any.
4. Confirm there are no guessed endpoints.
5. Confirm there is no fake signal data.
6. Confirm request cancellation works.
7. Confirm stale requests cannot overwrite newer requests.
8. Confirm authenticated requests use the existing web session.
9. Confirm the hook does not touch Telegram systems.
10. Confirm it works with the existing Signals page and trading components.

Do not merely describe the implementation.

Actually implement:

Fast/frontend/hooks/useSignals.ts

and verify the result.
