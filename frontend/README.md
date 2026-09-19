# KING ZARRY AI • Frontend

The web frontend for **KING ZARRY AI**, a personal AI intelligence system built around one AI core with multiple intelligence capabilities.

The interface is designed around a futuristic, cinematic, holographic AI experience while keeping the architecture ready for real backend integration.

## ✨ Product Vision

**ONE AI CORE → MANY INTELLIGENCE CAPABILITIES**

KING ZARRY AI is designed to bring multiple capabilities into one system:

- 🤖 AI Chat
- 🧠 Memory
- 👁️ Vision
- 🎙️ Voice
- 🧩 Agents
- 🛠️ Tools
- 📊 Market Intelligence
- 📈 Trading Signals
- 📰 News Intelligence
- 🔔 Alerts
- 🕘 History
- ⚙️ System Controls

Trading is one capability of the system, not the entire identity of the product.

---

## 🧱 Technology

The frontend uses:

- Next.js
- React
- TypeScript
- Tailwind CSS
- CSS/SVG-based visual effects

The application uses the Next.js App Router.

---

## 📁 Structure

```text
frontend/
├── app/
│   ├── alerts/
│   ├── chat/
│   ├── dashboard/
│   ├── history/
│   ├── login/
│   ├── markets/
│   ├── news/
│   ├── pricing/
│   ├── settings/
│   ├── signals/
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
│
├── components/
│   ├── alerts/
│   ├── chat/
│   ├── dashboard/
│   ├── layout/
│   ├── news/
│   ├── trading/
│   └── ui/
│
├── hooks/
│   ├── useAlerts.ts
│   ├── useAuth.ts
│   ├── useChat.ts
│   ├── useMarket.ts
│   └── useSignals.ts
│
├── lib/
│   ├── api.ts
│   ├── auth.ts
│   ├── constants.ts
│   └── utils.ts
│
├── public/
│   ├── icons/
│   └── images/
│
├── types/
│   ├── alerts.ts
│   ├── auth.ts
│   ├── chat.ts
│   ├── market.ts
│   ├── news.ts
│   └── trading.ts
│
├── .env.example
├── .gitignore
├── package.json
├── postcss.config.*
├── tailwind.config.*
├── tsconfig.json
└── README.md
