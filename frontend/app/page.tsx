import type { CSSProperties } from "react";

export const metadata = {
  title: "KING ZARRY AI",
  description: "Your intelligence. Amplified.",
};

/* ---------- deterministic geometry (no randomness at render time) ---------- */

const polar = (r: number, deg: number): [number, number] => {
  const a = ((deg - 90) * Math.PI) / 180;
  return [100 + r * Math.cos(a), 100 + r * Math.sin(a)];
};

const arc = (r: number, a0: number, a1: number): string => {
  const [x0, y0] = polar(r, a0);
  const [x1, y1] = polar(r, a1);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M${x0.toFixed(2)} ${y0.toFixed(2)} A${r} ${r} 0 ${large} 1 ${x1.toFixed(2)} ${y1.toFixed(2)}`;
};

const ticks = Array.from({ length: 120 }, (_, i) => {
  const long = i % 10 === 0;
  const [x1, y1] = polar(long ? 91 : 94.5, i * 3);
  const [x2, y2] = polar(99, i * 3);
  return {
    x1: x1.toFixed(2),
    y1: y1.toFixed(2),
    x2: x2.toFixed(2),
    y2: y2.toFixed(2),
    long,
  };
});

const nodesC = [20, 95, 170, 250, 310].map((d) => polar(72, d));

const particles = Array.from({ length: 42 }, (_, i) => {
  const s1 = (i * 9301 + 49297) % 233280;
  const s2 = (s1 * 9301 + 49297) % 233280;
  const s3 = (s2 * 9301 + 49297) % 233280;
  const r1 = s1 / 233280;
  const r2 = s2 / 233280;
  const r3 = s3 / 233280;
  return {
    left: (r1 * 100).toFixed(1),
    size: (1 + r2 * 2).toFixed(1),
    dur: (20 + r3 * 28).toFixed(1),
    delay: (-(r1 + r3) * 24).toFixed(1),
    drift: ((r2 - 0.5) * 90).toFixed(0),
  };
});

/* ---------- content ---------- */

const hudTags = [
  { text: "SYSTEM ONLINE", cls: "t-top" },
  { text: "NEURAL CORE", cls: "t-r", top: "21%" },
  { text: "MEMORY", cls: "t-l", top: "23%" },
  { text: "MARKET INTELLIGENCE", cls: "t-l", top: "78%" },
  { text: "ANALYSIS", cls: "t-r", top: "76%" },
  { text: "SIGNALS", cls: "t-bot" },
];

const telemetry = [
  { label: "NEURAL ACTIVITY", value: "98%", bar: true },
  { label: "MARKET SCAN", value: "ACTIVE" },
  { label: "MEMORY", value: "ONLINE" },
  { label: "SIGNAL ENGINE", value: "READY" },
  { label: "AI CORE", value: "STABLE" },
];

type Tone = "bull" | "bear" | "neu" | "scan";

const markets: { sym: string; spin: string; rows: [string, string, Tone][] }[] = [
  {
    sym: "BTC",
    spin: "34s",
    rows: [
      ["STRUCTURE", "BULLISH", "bull"],
      ["MOMENTUM", "BULLISH", "bull"],
      ["VOLATILITY", "NEUTRAL", "neu"],
      ["SIGNAL STATUS", "SCANNING", "scan"],
    ],
  },
  {
    sym: "ETH",
    spin: "46s",
    rows: [
      ["STRUCTURE", "NEUTRAL", "neu"],
      ["MOMENTUM", "SCANNING", "scan"],
      ["VOLATILITY", "BEARISH", "bear"],
      ["SIGNAL STATUS", "SCANNING", "scan"],
    ],
  },
  {
    sym: "SOL",
    spin: "28s",
    rows: [
      ["STRUCTURE", "BULLISH", "bull"],
      ["MOMENTUM", "NEUTRAL", "neu"],
      ["VOLATILITY", "SCANNING", "scan"],
      ["SIGNAL STATUS", "NEUTRAL", "neu"],
    ],
  },
  {
    sym: "XAUUSD",
    spin: "52s",
    rows: [
      ["STRUCTURE", "BEARISH", "bear"],
      ["MOMENTUM", "SCANNING", "scan"],
      ["VOLATILITY", "NEUTRAL", "neu"],
      ["SIGNAL STATUS", "SCANNING", "scan"],
    ],
  },
];

const ladder = [
  { k: "TP3", cls: "tp", w: "92%" },
  { k: "TP2", cls: "tp", w: "76%" },
  { k: "TP1", cls: "tp", w: "60%" },
  { k: "ENTRY", cls: "en", w: "44%" },
  { k: "SL", cls: "sl", w: "26%" },
];

const memMain = [
  { x: 140, y: 110, label: "CONVERSATIONS" },
  { x: 660, y: 110, label: "PREFERENCES" },
  { x: 140, y: 370, label: "TRADING" },
  { x: 660, y: 370, label: "CONTEXT" },
];

const memSmall = [
  [270, 55],
  [545, 50],
  [80, 240],
  [720, 240],
  [265, 430],
  [540, 435],
  [300, 175],
  [500, 175],
  [300, 305],
  [500, 305],
];

const memEdges: [number, number, number, number][] = [
  [400, 240, 140, 110],
  [400, 240, 660, 110],
  [400, 240, 140, 370],
  [400, 240, 660, 370],
  [140, 110, 270, 55],
  [660, 110, 545, 50],
  [140, 110, 80, 240],
  [660, 370, 720, 240],
  [140, 370, 265, 430],
  [660, 370, 540, 435],
  [400, 240, 300, 175],
  [400, 240, 500, 175],
  [400, 240, 300, 305],
  [400, 240, 500, 305],
  [80, 240, 140, 370],
  [720, 240, 660, 110],
];

/* ---------- reusable HUD ring artwork ---------- */

function Rings({ id }: { id: string }) {
  return (
    <>
      <svg className="kz-layer kz-spin-slow" viewBox="0 0 200 200" aria-hidden="true">
        <circle cx="100" cy="100" r="99.4" fill="none" stroke="rgba(79,216,255,.22)" strokeWidth=".25" />
        {ticks.map((t, i) => (
          <line
            key={`${id}-t-${i}`}
            x1={t.x1}
            y1={t.y1}
            x2={t.x2}
            y2={t.y2}
            stroke={t.long ? "rgba(140,232,255,.75)" : "rgba(79,216,255,.32)"}
            strokeWidth={t.long ? 0.5 : 0.25}
          />
        ))}
      </svg>
      <svg className="kz-layer kz-spin-rev" viewBox="0 0 200 200" aria-hidden="true">
        <circle cx="100" cy="100" r="86" fill="none" stroke="rgba(79,216,255,.3)" strokeWidth=".3" strokeDasharray="1 5" />
        <path d={arc(82, 10, 78)} fill="none" stroke="rgba(120,225,255,.7)" strokeWidth=".9" strokeLinecap="round" />
        <path d={arc(82, 130, 168)} fill="none" stroke="rgba(79,216,255,.45)" strokeWidth=".6" strokeLinecap="round" />
        <path d={arc(82, 205, 292)} fill="none" stroke="rgba(120,225,255,.6)" strokeWidth=".9" strokeLinecap="round" />
      </svg>
      <svg className="kz-layer kz-spin-mid" viewBox="0 0 200 200" aria-hidden="true">
        <circle cx="100" cy="100" r="72" fill="none" stroke="rgba(79,216,255,.38)" strokeWidth=".4" strokeDasharray="24 8 3 8" />
        {nodesC.map(([x, y], i) => (
          <circle key={`${id}-n-${i}`} cx={x.toFixed(2)} cy={y.toFixed(2)} r="1.4" fill="#8ff0ff" />
        ))}
      </svg>
      <svg className="kz-layer" viewBox="0 0 200 200" aria-hidden="true">
        <circle cx="100" cy="100" r="60" fill="none" stroke="rgba(79,216,255,.18)" strokeWidth=".3" />
        <line x1="100" y1="2" x2="100" y2="34" stroke="rgba(79,216,255,.35)" strokeWidth=".3" />
        <line x1="100" y1="166" x2="100" y2="198" stroke="rgba(79,216,255,.35)" strokeWidth=".3" />
        <line x1="2" y1="100" x2="34" y2="100" stroke="rgba(79,216,255,.35)" strokeWidth=".3" />
        <line x1="166" y1="100" x2="198" y2="100" stroke="rgba(79,216,255,.35)" strokeWidth=".3" />
      </svg>
    </>
  );
}

/* ---------- page ---------- */

export default function Page() {
  return (
    <main className="kz">
      <style dangerouslySetInnerHTML={{ __html: css }} />

      {/* ambient background */}
      <div className="kz-ambient" aria-hidden="true">
        <div className="kz-grid" />
        <div className="kz-vignette" />
        {particles.map((p, i) => (
          <span
            key={i}
            className="kz-particle"
            style={
              {
                left: `${p.left}%`,
                width: `${p.size}px`,
                height: `${p.size}px`,
                animationDuration: `${p.dur}s`,
                animationDelay: `${p.delay}s`,
                "--dx": `${p.drift}px`,
              } as CSSProperties
            }
          />
        ))}
        <div className="kz-scan" />
      </div>

      {/* navigation */}
      <header className="kz-nav">
        <a className="kz-brand" href="#system" aria-label="KING ZARRY AI">
          <span className="kz-brand-mark" aria-hidden="true" />
          KING ZARRY AI
        </a>
        <span className="kz-status">
          <i className="kz-dot" aria-hidden="true" /> ONLINE
        </span>
        <nav className="kz-links" aria-label="Primary">
          <a href="#system">SYSTEM</a>
          <a href="#markets">MARKETS</a>
          <a href="#ai">AI</a>
          <a href="#signals">SIGNALS</a>
        </nav>
      </header>

      {/* ---------------- HERO ---------------- */}
      <section id="system" className="kz-hero">
        <div className="kz-wrap">
          <div className="kz-stage">
            <div className="kz-halo" aria-hidden="true" />
            <div className="kz-sweep" aria-hidden="true" />
            <Rings id="hero" />

            <div className="kz-orb" aria-hidden="true">
              <div className="kz-orb-ring" />
              <div className="kz-orb-ring kz-orb-ring2" />
              <span className="kz-orb-text">KZ</span>
            </div>

            {hudTags.map((t) => (
              <span
                key={t.text}
                className={`kz-tag ${t.cls}`}
                style={t.top ? { top: t.top } : undefined}
                aria-hidden="true"
              >
                <i className="kz-dot" />
                {t.text}
              </span>
            ))}
          </div>

          <div className="kz-copy">
            <h1 className="kz-title">KING ZARRY AI</h1>
            <p className="kz-tagline">YOUR INTELLIGENCE. AMPLIFIED.</p>
            <p className="kz-lede">
              An advanced AI command centre for understanding markets, analysing information and thinking with you.
            </p>
            <div className="kz-actions">
              <button type="button" className="kz-btn kz-btn-primary">
                <span>ENTER SYSTEM</span>
              </button>
              <a href="#ai" className="kz-btn kz-btn-ghost">
                <span>EXPLORE INTELLIGENCE</span>
              </a>
            </div>
          </div>

          <div className="kz-dock">
            <div className="kz-glass kz-panel p1">
              <span className="kz-mini">MARKET INTELLIGENCE</span>
              <strong className="kz-panel-big">BTC/USD</strong>
              <span className="kz-panel-state">
                <i className="kz-dot" /> ANALYSIS READY
              </span>
              <span className="kz-bar" aria-hidden="true"><b /></span>
            </div>
            <div className="kz-glass kz-panel p2">
              <span className="kz-mini">AI SIGNAL ENGINE</span>
              <strong className="kz-panel-big">15M</strong>
              <span className="kz-panel-state">
                <i className="kz-dot" /> READY
              </span>
              <span className="kz-bar" aria-hidden="true"><b /></span>
            </div>
            <div className="kz-glass kz-panel p3">
              <span className="kz-mini">MEMORY</span>
              <strong className="kz-panel-big kz-panel-sm">PERSONAL CONTEXT</strong>
              <span className="kz-panel-state">
                <i className="kz-dot" /> ONLINE
              </span>
              <span className="kz-bar" aria-hidden="true"><b /></span>
            </div>
            <div className="kz-tele" role="group" aria-label="Decorative system telemetry">
              {telemetry.map((t) => (
                <div className="kz-tele-row" key={t.label}>
                  <span>
                    <i className="kz-dot" /> {t.label}
                  </span>
                  <em>{t.value}</em>
                  {t.bar ? (
                    <span className="kz-tele-bar" aria-hidden="true"><b /></span>
                  ) : null}
                </div>
              ))}
              <p className="kz-fine">DECORATIVE DEMO VALUES</p>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- CONVERSATION ---------------- */}
      <section id="ai" className="kz-sec">
        <div className="kz-inner">
          <h2 className="kz-h2">ASK YOUR INTELLIGENCE.</h2>
          <p className="kz-sub">A preview of how a conversation with KING ZARRY AI will feel. Nothing here is live.</p>

          <div className="kz-glass kz-chat">
            <div className="kz-chat-head">
              <span><i className="kz-dot" /> SECURE CHANNEL</span>
              <span>DEMO SESSION</span>
            </div>

            <div className="kz-msg-user">
              <span className="kz-who">USER</span>
              <p>What is the market telling me?</p>
            </div>

            <div className="kz-msg-ai">
              <div className="kz-ai-orb" aria-hidden="true">
                <span />
              </div>
              <div className="kz-ai-body">
                <span className="kz-who">KZ AI</span>
                <p className="kz-line l1">Scanning market structure…</p>
                <p className="kz-line l2">Momentum detected.</p>
                <p className="kz-line l3">Waiting for confirmation.<span className="kz-caret" aria-hidden="true" /></p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ---------------- MARKETS ---------------- */}
      <section id="markets" className="kz-sec">
        <div className="kz-inner">
          <h2 className="kz-h2">THE MARKET IS ALWAYS SPEAKING.</h2>
          <p className="kz-sub">
            Structure, momentum, volatility and signal status, shown as interface states. These are demonstrations, not live prices.
          </p>

          <div className="kz-markets">
            {markets.map((m) => (
              <article className="kz-glass kz-mkt" key={m.sym}>
                <div className="kz-mkt-head">
                  <div className="kz-gauge" aria-hidden="true">
                    <svg viewBox="0 0 64 64" style={{ animationDuration: m.spin }}>
                      <circle cx="32" cy="32" r="27" fill="none" stroke="rgba(79,216,255,.2)" strokeWidth="1" strokeDasharray="1 4" />
                      <path d="M32 5 A27 27 0 0 1 59 32" fill="none" stroke="#5fe0ff" strokeWidth="1.6" strokeLinecap="round" />
                      <path d="M32 59 A27 27 0 0 1 5 32" fill="none" stroke="rgba(95,224,255,.5)" strokeWidth="1.2" strokeLinecap="round" />
                    </svg>
                    <i />
                  </div>
                  <div>
                    <h3>{m.sym}</h3>
                    <span className="kz-mini">DEMO STATE</span>
                  </div>
                </div>
                <ul>
                  {m.rows.map(([k, v, tone]) => (
                    <li key={k}>
                      <span>{k}</span>
                      <b className={`kz-chip ${tone}`}>
                        <i />
                        {v}
                      </b>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ---------------- SIGNAL ENGINE ---------------- */}
      <section id="signals" className="kz-sec">
        <div className="kz-inner">
          <h2 className="kz-h2">WHEN THE SIGNAL APPEARS.</h2>
          <p className="kz-sub">Entry, stop loss and targets in a single view. Placeholder values only.</p>

          <div className="kz-glass kz-signal">
            <div className="kz-sig-head">
              <div className="kz-sig-pair">
                <strong>BTC/USD</strong>
                <span className="kz-badge-buy">BUY</span>
                <span className="kz-badge-tf">15M</span>
              </div>
              <span className="kz-mini"><i className="kz-dot" /> SIGNAL GENERATED</span>
            </div>

            <div className="kz-sig-body">
              <div className="kz-ladder">
                {ladder.map((r) => (
                  <div className={`kz-rung ${r.cls}`} key={r.k}>
                    <span className="kz-rung-k">{r.k}</span>
                    <span className="kz-rung-line" style={{ width: r.w }} aria-hidden="true" />
                    <span className="kz-rung-v">0000.00</span>
                  </div>
                ))}
                <span className="kz-scanner" aria-hidden="true" />
              </div>

              <div className="kz-conf">
                <svg viewBox="0 0 100 100" aria-hidden="true">
                  <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(79,216,255,.14)" strokeWidth="4" />
                  <circle className="kz-conf-arc" cx="50" cy="50" r="42" fill="none" stroke="#63e2ff" strokeWidth="4" strokeLinecap="round" strokeDasharray="263.9" strokeDashoffset="34.3" transform="rotate(-90 50 50)" />
                  <circle cx="50" cy="50" r="33" fill="none" stroke="rgba(79,216,255,.2)" strokeWidth=".5" strokeDasharray="1 4" />
                </svg>
                <div className="kz-conf-txt">
                  <b>87%</b>
                  <span>CONFIDENCE</span>
                </div>
              </div>
            </div>

            <p className="kz-fine kz-fine-wide">
              PLACEHOLDER VALUES. NOT LIVE DATA. NOT FINANCIAL ADVICE.
            </p>
          </div>
        </div>
      </section>

      {/* ---------------- MEMORY ---------------- */}
      <section id="memory" className="kz-sec">
        <div className="kz-inner">
          <h2 className="kz-h2">IT REMEMBERS.</h2>
          <p className="kz-sub">
            In time, KING ZARRY AI is designed to hold your conversations, preferences and context in one connected memory.
          </p>

          <div className="kz-glass kz-mem">
            <svg viewBox="0 0 800 480" role="img" aria-label="Neural memory network connecting conversations, preferences, trading and context to a central memory node">
              <defs>
                <radialGradient id="kzCore" cx="50%" cy="45%" r="60%">
                  <stop offset="0%" stopColor="rgba(120,230,255,.55)" />
                  <stop offset="60%" stopColor="rgba(30,90,170,.35)" />
                  <stop offset="100%" stopColor="rgba(4,12,24,.9)" />
                </radialGradient>
              </defs>
              {memEdges.map(([x1, y1, x2, y2], i) => (
                <line
                  key={i}
                  className="kz-link"
                  style={{ animationDelay: `${-(i % 6) * 0.5}s` }}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                />
              ))}
              {memSmall.map(([x, y], i) => (
                <circle
                  key={i}
                  className="kz-mnode"
                  style={{ animationDelay: `${-(i % 5) * 0.8}s` }}
                  cx={x}
                  cy={y}
                  r="5"
                />
              ))}
              {memMain.map((n) => (
                <g key={n.label}>
                  <circle className="kz-mhalo" cx={n.x} cy={n.y} r="26" />
                  <circle cx={n.x} cy={n.y} r="14" fill="rgba(5,16,30,.9)" stroke="#63e2ff" strokeWidth="1.5" />
                  <circle cx={n.x} cy={n.y} r="4.5" fill="#bff6ff" />
                  <text className="kz-mtext" x={n.x} y={n.y + 52} textAnchor="middle">
                    {n.label}
                  </text>
                </g>
              ))}
              <circle className="kz-mcore-ring" cx="400" cy="240" r="72" />
              <circle cx="400" cy="240" r="52" fill="url(#kzCore)" stroke="#63e2ff" strokeWidth="1.5" />
              <text className="kz-mtext kz-mtext-core" x="400" y="247" textAnchor="middle">
                MEMORY
              </text>
            </svg>
          </div>
        </div>
      </section>

      {/* ---------------- FINAL ---------------- */}
      <section className="kz-final" id="enter">
        <div className="kz-final-rings" aria-hidden="true">
          <Rings id="final" />
        </div>
        <div className="kz-final-inner">
          <h2 className="kz-final-title">INITIALIZE YOUR INTELLIGENCE.</h2>
          <p className="kz-final-small">KING ZARRY AI</p>
          <button type="button" className="kz-btn kz-btn-primary kz-btn-lg">
            <span>ENTER KING ZARRY AI</span>
          </button>
        </div>
        <p className="kz-foot">Visual foundation. All values shown are decorative.</p>
      </section>
    </main>
  );
}

/* ---------- styles ---------- */

const css = `
.kz{
  --c:#4fd8ff; --c2:#2f86ff; --ink:#d6edf7; --dim:#7b98ab; --line:rgba(79,216,255,.22);
  --bg:#03060c; --bull:#5fe0ff; --bear:#ff6b8a; --neu:#8fa8ba; --scan:#4f8bff;
  --display:"Eurostile","Bank Gothic","Segoe UI Variable Display","Segoe UI","Helvetica Neue",Arial,sans-serif;
  --mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace;
  position:relative; min-height:100vh; overflow-x:clip; color:var(--ink);
  font-family:var(--display); background:var(--bg); -webkit-font-smoothing:antialiased;
}
.kz *,.kz *::before,.kz *::after{box-sizing:border-box}
.kz h1,.kz h2,.kz h3,.kz p,.kz ul{margin:0;padding:0}
.kz ul{list-style:none}
.kz a{color:inherit;text-decoration:none}
.kz button{font-family:inherit}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}

/* ambient */
.kz-ambient{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;
  background:
    radial-gradient(80% 60% at 50% 18%,rgba(24,72,150,.32),transparent 70%),
    radial-gradient(60% 50% at 85% 80%,rgba(10,50,110,.22),transparent 70%),
    linear-gradient(180deg,#02050a 0%,#040b17 55%,#02050a 100%)}
.kz-grid{position:absolute;inset:-2px;
  background-image:linear-gradient(rgba(79,216,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(79,216,255,.05) 1px,transparent 1px);
  background-size:56px 56px;
  -webkit-mask:radial-gradient(ellipse at 50% 30%,#000 10%,transparent 75%);mask:radial-gradient(ellipse at 50% 30%,#000 10%,transparent 75%);
  animation:kz-grid 40s linear infinite}
.kz-vignette{position:absolute;inset:0;background:radial-gradient(ellipse at center,transparent 45%,rgba(0,0,0,.7) 100%)}
.kz-particle{position:absolute;bottom:-10px;border-radius:50%;background:#8fefff;box-shadow:0 0 8px rgba(79,216,255,.9);opacity:0;
  animation:kz-rise linear infinite}
.kz-scan{position:absolute;left:0;right:0;height:26vh;top:-30vh;
  background:linear-gradient(180deg,transparent,rgba(79,216,255,.05),transparent);animation:kz-scan 11s linear infinite}
.kz-ambient::after{content:"";position:absolute;inset:0;
  background:repeating-linear-gradient(180deg,rgba(255,255,255,.018) 0,rgba(255,255,255,.018) 1px,transparent 1px,transparent 3px)}

/* nav */
.kz-nav{position:absolute;top:0;left:0;right:0;z-index:20;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;
  padding:18px 20px;gap:10px 16px}
.kz-brand{display:inline-flex;align-items:center;gap:10px;font-size:.78rem;letter-spacing:.32em;font-weight:600;color:#eafcff}
.kz-brand-mark{width:14px;height:14px;border:1px solid var(--c);border-radius:50%;position:relative;box-shadow:0 0 10px rgba(79,216,255,.6)}
.kz-brand-mark::after{content:"";position:absolute;inset:3px;border-radius:50%;background:var(--c)}
.kz-status{display:inline-flex;align-items:center;gap:8px;font-family:var(--mono);font-size:.68rem;letter-spacing:.24em;color:var(--c)}
.kz-links{order:3;width:100%;display:flex;justify-content:space-between;gap:8px;font-size:.66rem;letter-spacing:.28em;color:var(--dim)}
.kz-links a{padding:6px 2px;transition:color .3s,text-shadow .3s}
.kz-links a:hover,.kz-links a:focus-visible{color:#eafcff;text-shadow:0 0 12px rgba(79,216,255,.9)}
.kz a:focus-visible,.kz button:focus-visible{outline:2px solid var(--c);outline-offset:4px}
.kz-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--c);box-shadow:0 0 8px var(--c);animation:kz-blink 2.6s ease-in-out infinite;flex:none}

/* hero */
.kz-hero{position:relative;z-index:1;padding:104px 0 32px}
.kz-wrap{position:relative;max-width:1240px;margin:0 auto}
.kz-stage{--s:min(94vw,66svh,660px);position:relative;width:var(--s);height:var(--s);margin:0 auto}
.kz-layer{position:absolute;inset:0;width:100%;height:100%;display:block}
.kz-spin-slow{animation:kz-spin 120s linear infinite}
.kz-spin-rev{animation:kz-spin 70s linear infinite reverse}
.kz-spin-mid{animation:kz-spin 46s linear infinite}
.kz-halo{position:absolute;inset:-12%;border-radius:50%;background:radial-gradient(circle,rgba(47,134,255,.26),rgba(20,70,160,.1) 45%,transparent 68%);animation:kz-breathe 7s ease-in-out infinite}
.kz-sweep{position:absolute;inset:8%;border-radius:50%;
  background:conic-gradient(from 0deg,rgba(79,216,255,0) 0deg,rgba(79,216,255,.16) 50deg,rgba(79,216,255,0) 51deg);
  -webkit-mask:radial-gradient(circle,transparent 24%,#000 26%);mask:radial-gradient(circle,transparent 24%,#000 26%);
  animation:kz-spin 10s linear infinite}
.kz-orb{position:absolute;inset:32%;border-radius:50%;display:grid;place-items:center;
  background:radial-gradient(circle at 50% 38%,rgba(120,232,255,.42),rgba(30,100,190,.3) 42%,rgba(3,10,20,.92) 74%);
  border:1px solid rgba(120,232,255,.55);
  box-shadow:0 0 70px rgba(79,216,255,.38),0 0 160px rgba(47,134,255,.22),inset 0 0 46px rgba(79,216,255,.3);
  animation:kz-pulse 5.5s ease-in-out infinite}
.kz-orb-ring{position:absolute;inset:7%;border-radius:50%;
  background:conic-gradient(from 0deg,transparent 0deg,rgba(150,240,255,.9) 70deg,transparent 71deg);
  -webkit-mask:radial-gradient(farthest-side,transparent calc(100% - 2px),#000 calc(100% - 1px));mask:radial-gradient(farthest-side,transparent calc(100% - 2px),#000 calc(100% - 1px));
  animation:kz-spin 7s linear infinite}
.kz-orb-ring2{inset:16%;animation-duration:11s;animation-direction:reverse;opacity:.7}
.kz-orb-text{font-size:calc(var(--s)*.115);font-weight:300;letter-spacing:.14em;padding-left:.14em;color:#eefcff;
  text-shadow:0 0 16px rgba(79,216,255,.95),0 0 46px rgba(79,216,255,.55)}

.kz-tag{position:absolute;display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:.6rem;letter-spacing:.22em;color:rgba(160,225,245,.85);white-space:nowrap}
.kz-tag .kz-dot{width:4px;height:4px}
.kz-tag.t-top{top:1%;left:50%;transform:translateX(-50%)}
.kz-tag.t-bot{bottom:1%;left:50%;transform:translateX(-50%)}
.kz-tag.t-l{left:0}
.kz-tag.t-r{right:0}

.kz-copy{position:relative;z-index:2;text-align:center;padding:0 20px;margin-top:-1vh}
.kz-title{font-size:clamp(1.7rem,7vw,4.6rem);font-weight:200;letter-spacing:.17em;padding-left:.17em;color:#effcff;
  text-shadow:0 0 24px rgba(79,216,255,.55),0 0 80px rgba(47,134,255,.4)}
.kz-tagline{margin-top:14px;font-size:clamp(.66rem,2.2vw,.98rem);letter-spacing:.4em;padding-left:.4em;color:var(--c);text-shadow:0 0 14px rgba(79,216,255,.6)}
.kz-lede{margin:18px auto 0;max-width:46ch;line-height:1.7;color:var(--dim);font-size:clamp(.88rem,2.4vw,1.02rem)}
.kz-actions{display:flex;flex-wrap:wrap;justify-content:center;gap:16px;margin-top:32px}

/* buttons */
.kz-btn{--cut:12px;position:relative;isolation:isolate;display:inline-flex;align-items:center;justify-content:center;cursor:pointer;border:0;
  padding:16px 30px;min-height:52px;font-size:.74rem;letter-spacing:.3em;font-weight:600;color:#eafcff;
  background:linear-gradient(135deg,rgba(120,232,255,.95),rgba(47,134,255,.55) 55%,rgba(120,232,255,.9));
  clip-path:polygon(var(--cut) 0,100% 0,100% calc(100% - var(--cut)),calc(100% - var(--cut)) 100%,0 100%,0 var(--cut));
  transition:filter .35s,transform .35s}
.kz-btn::before{content:"";position:absolute;inset:1px;z-index:-1;
  clip-path:polygon(var(--cut) 0,100% 0,100% calc(100% - var(--cut)),calc(100% - var(--cut)) 100%,0 100%,0 var(--cut));
  background:linear-gradient(180deg,rgba(6,20,38,.94),rgba(4,12,24,.96));transition:background .35s}
.kz-btn::after{content:"";position:absolute;top:0;bottom:0;left:-40%;width:30%;z-index:-1;
  background:linear-gradient(90deg,transparent,rgba(120,232,255,.35),transparent);transform:skewX(-20deg);transition:left .7s ease}
.kz-btn span{padding-left:.3em;text-shadow:0 0 12px rgba(79,216,255,.6)}
.kz-btn:hover,.kz-btn:focus-visible{filter:drop-shadow(0 0 14px rgba(79,216,255,.55));transform:translateY(-2px)}
.kz-btn:hover::after{left:120%}
.kz-btn-primary::before{background:linear-gradient(180deg,rgba(20,80,130,.85),rgba(6,26,50,.95))}
.kz-btn-primary:hover::before{background:linear-gradient(180deg,rgba(30,110,170,.9),rgba(8,34,64,.95))}
.kz-btn-ghost{background:linear-gradient(135deg,rgba(79,216,255,.5),rgba(79,216,255,.15))}
.kz-btn-lg{padding:20px 40px;font-size:.82rem}

/* dock (panels + telemetry) */
.kz-dock{display:grid;grid-template-columns:1fr;gap:12px;padding:0 16px;max-width:520px;margin:34px auto 0;position:relative;z-index:2}
.kz-glass{position:relative;background:linear-gradient(160deg,rgba(22,66,120,.26),rgba(4,12,24,.55));
  border:1px solid var(--line);border-radius:4px;-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);
  box-shadow:0 0 40px rgba(20,80,160,.12),inset 0 0 30px rgba(79,216,255,.04);transition:border-color .4s,box-shadow .4s,transform .4s}
.kz-glass::before,.kz-glass::after{content:"";position:absolute;width:14px;height:14px;pointer-events:none}
.kz-glass::before{top:-1px;left:-1px;border-top:2px solid var(--c);border-left:2px solid var(--c)}
.kz-glass::after{bottom:-1px;right:-1px;border-bottom:2px solid var(--c);border-right:2px solid var(--c)}
.kz-glass:hover{border-color:rgba(79,216,255,.5);box-shadow:0 0 50px rgba(47,134,255,.22),inset 0 0 30px rgba(79,216,255,.07)}
.kz-panel{padding:16px 18px;display:flex;flex-direction:column;gap:8px;animation:kz-float 7s ease-in-out infinite alternate}
.kz-panel.p2{animation-delay:-2.4s}.kz-panel.p3{animation-delay:-4.6s}
.kz-mini{font-family:var(--mono);font-size:.6rem;letter-spacing:.24em;color:var(--dim)}
.kz-panel-big{font-size:1.5rem;font-weight:300;letter-spacing:.14em;color:#effcff;text-shadow:0 0 14px rgba(79,216,255,.5)}
.kz-panel-sm{font-size:1.02rem;letter-spacing:.16em}
.kz-panel-state{display:inline-flex;align-items:center;gap:8px;font-family:var(--mono);font-size:.64rem;letter-spacing:.2em;color:var(--c)}
.kz-bar{display:block;height:2px;background:rgba(79,216,255,.12);overflow:hidden;margin-top:2px}
.kz-bar b{display:block;height:100%;width:38%;background:linear-gradient(90deg,transparent,var(--c),transparent);animation:kz-bar 3.8s ease-in-out infinite}
.kz-tele{padding:6px 4px}
.kz-tele-row{position:relative;display:flex;justify-content:space-between;align-items:center;gap:10px;padding:8px 2px;border-bottom:1px solid rgba(79,216,255,.1);
  font-family:var(--mono);font-size:.62rem;letter-spacing:.2em;color:var(--dim)}
.kz-tele-row span{display:inline-flex;align-items:center;gap:8px}
.kz-tele-row em{font-style:normal;color:var(--c)}
.kz-tele-bar{position:absolute;left:0;right:0;bottom:-1px;height:1px;background:transparent;display:block}
.kz-tele-bar b{display:block;height:1px;width:98%;background:var(--c);box-shadow:0 0 8px var(--c);animation:kz-meter 5s ease-in-out infinite}
.kz-fine{margin-top:10px;font-family:var(--mono);font-size:.56rem;letter-spacing:.24em;color:rgba(123,152,171,.7)}
.kz-fine-wide{text-align:center;margin:22px 0 0}

/* sections */
.kz-sec{position:relative;z-index:1;padding:clamp(64px,11vw,130px) 20px}
.kz-inner{max-width:1040px;margin:0 auto}
.kz-h2{font-size:clamp(1.5rem,5.2vw,3.1rem);font-weight:200;letter-spacing:.1em;line-height:1.2;color:#effcff;text-shadow:0 0 30px rgba(79,216,255,.35)}
.kz-sub{margin-top:16px;max-width:56ch;line-height:1.7;color:var(--dim);font-size:clamp(.88rem,2.3vw,1rem)}
.kz-who{display:block;font-family:var(--mono);font-size:.6rem;letter-spacing:.26em;color:var(--dim);margin-bottom:6px}

/* chat */
.kz-chat{margin-top:40px;padding:clamp(18px,4vw,34px);max-width:760px}
.kz-chat-head{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;padding-bottom:16px;margin-bottom:26px;border-bottom:1px solid rgba(79,216,255,.14);
  font-family:var(--mono);font-size:.6rem;letter-spacing:.24em;color:var(--dim)}
.kz-chat-head span{display:inline-flex;align-items:center;gap:8px}
.kz-msg-user{margin-left:auto;max-width:86%;text-align:right}
.kz-msg-user p{display:inline-block;text-align:left;padding:12px 18px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);border-radius:2px 14px 2px 14px;line-height:1.5;color:#eaf6fb}
.kz-msg-ai{display:flex;gap:16px;margin-top:30px;align-items:flex-start}
.kz-ai-orb{position:relative;flex:none;width:46px;height:46px;border-radius:50%;
  background:radial-gradient(circle at 50% 40%,rgba(150,240,255,.9),rgba(47,134,255,.5) 55%,rgba(4,12,24,.9));
  box-shadow:0 0 24px rgba(79,216,255,.7),0 0 60px rgba(47,134,255,.35);animation:kz-pulse 3.6s ease-in-out infinite}
.kz-ai-orb::before{content:"";position:absolute;inset:-7px;border-radius:50%;border:1px dashed rgba(79,216,255,.5);animation:kz-spin 12s linear infinite}
.kz-ai-orb span{position:absolute;inset:-14px;border-radius:50%;border:1px solid rgba(79,216,255,.18);animation:kz-ring 3.6s ease-out infinite}
.kz-ai-body{padding:14px 18px;flex:1;min-width:0;border:1px solid rgba(79,216,255,.28);border-radius:2px 2px 14px 2px;
  background:linear-gradient(160deg,rgba(30,100,170,.22),rgba(4,14,28,.6));box-shadow:inset 0 0 30px rgba(79,216,255,.06)}
.kz-line{margin-top:6px;line-height:1.5;color:#e2f8ff;font-size:1rem;opacity:1}
.kz-line.l1{animation:kz-l1 15s ease infinite}
.kz-line.l2{animation:kz-l2 15s ease infinite}
.kz-line.l3{animation:kz-l3 15s ease infinite}
.kz-caret{display:inline-block;width:8px;height:1em;margin-left:6px;vertical-align:-2px;background:var(--c);box-shadow:0 0 8px var(--c);animation:kz-caret 1s steps(2) infinite}

/* markets */
.kz-markets{margin-top:42px;display:grid;grid-template-columns:1fr;gap:16px}
.kz-mkt{padding:20px}
.kz-mkt:hover{transform:translateY(-3px)}
.kz-mkt-head{display:flex;align-items:center;gap:16px;padding-bottom:16px;margin-bottom:6px;border-bottom:1px solid rgba(79,216,255,.12)}
.kz-mkt h3{font-size:1.2rem;font-weight:300;letter-spacing:.22em;color:#effcff}
.kz-gauge{position:relative;width:54px;height:54px;flex:none}
.kz-gauge svg{position:absolute;inset:0;width:100%;height:100%;animation:kz-spin linear infinite}
.kz-gauge i{position:absolute;inset:22px;border-radius:50%;background:var(--c);box-shadow:0 0 12px var(--c);animation:kz-blink 3s ease-in-out infinite}
.kz-mkt li{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:11px 0;border-bottom:1px solid rgba(79,216,255,.07);
  font-size:.66rem;letter-spacing:.2em;color:var(--dim)}
.kz-mkt li:last-child{border-bottom:0}
.kz-chip{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:.62rem;letter-spacing:.16em;font-weight:500}
.kz-chip i{width:6px;height:6px;border-radius:50%;background:currentColor;box-shadow:0 0 8px currentColor}
.kz-chip.bull{color:var(--bull)}.kz-chip.bear{color:var(--bear)}.kz-chip.neu{color:var(--neu)}
.kz-chip.scan{color:var(--scan)}.kz-chip.scan i{animation:kz-blink 1.4s ease-in-out infinite}

/* signal */
.kz-signal{margin-top:40px;padding:clamp(18px,4vw,36px);max-width:860px}
.kz-sig-head{display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;align-items:center;padding-bottom:18px;margin-bottom:24px;border-bottom:1px solid rgba(79,216,255,.14)}
.kz-sig-head .kz-mini{display:inline-flex;align-items:center;gap:8px}
.kz-sig-pair{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.kz-sig-pair strong{font-size:1.5rem;font-weight:300;letter-spacing:.16em;color:#effcff}
.kz-badge-buy{padding:5px 14px;font-family:var(--mono);font-size:.7rem;letter-spacing:.24em;color:#04131f;background:var(--c);box-shadow:0 0 20px rgba(79,216,255,.55);border-radius:2px;font-weight:700}
.kz-badge-tf{padding:5px 12px;font-family:var(--mono);font-size:.7rem;letter-spacing:.2em;color:var(--c);border:1px solid var(--line);border-radius:2px}
.kz-sig-body{display:grid;grid-template-columns:1fr;gap:28px;align-items:center}
.kz-ladder{position:relative;display:flex;flex-direction:column;gap:14px;padding-left:0}
.kz-rung{display:grid;grid-template-columns:54px 1fr auto;align-items:center;gap:12px;font-family:var(--mono);font-size:.68rem;letter-spacing:.18em}
.kz-rung-line{display:block;height:1px;justify-self:start;background:linear-gradient(90deg,currentColor,transparent);box-shadow:0 0 8px currentColor}
.kz-rung.tp{color:var(--bull)}.kz-rung.en{color:#eaf6fb}.kz-rung.sl{color:var(--bear)}
.kz-rung-v{color:var(--dim)}
.kz-scanner{position:absolute;left:0;right:0;height:26px;top:-10px;pointer-events:none;background:linear-gradient(180deg,transparent,rgba(79,216,255,.14),transparent);animation:kz-ladder 6s ease-in-out infinite alternate}
.kz-conf{position:relative;width:min(190px,54vw);aspect-ratio:1;margin:0 auto}
.kz-conf svg{width:100%;height:100%;display:block;filter:drop-shadow(0 0 10px rgba(79,216,255,.5))}
.kz-conf-arc{animation:kz-draw 2.6s ease-out both}
.kz-conf-txt{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px}
.kz-conf-txt b{font-size:2rem;font-weight:200;letter-spacing:.06em;color:#effcff;text-shadow:0 0 16px rgba(79,216,255,.7)}
.kz-conf-txt span{font-family:var(--mono);font-size:.56rem;letter-spacing:.24em;color:var(--dim)}

/* memory */
.kz-mem{margin-top:40px;padding:clamp(8px,3vw,28px);max-width:900px}
.kz-mem svg{display:block;width:100%;height:auto}
.kz-link{stroke:rgba(79,216,255,.4);stroke-width:1;stroke-dasharray:4 8;animation:kz-flow 3s linear infinite}
.kz-mnode{fill:#8fefff;animation:kz-blink 4s ease-in-out infinite}
.kz-mhalo{fill:rgba(79,216,255,.07);stroke:rgba(79,216,255,.3);stroke-width:1;stroke-dasharray:2 5;transform-box:fill-box;transform-origin:center;animation:kz-spin 30s linear infinite}
.kz-mcore-ring{fill:none;stroke:rgba(79,216,255,.4);stroke-width:1;stroke-dasharray:10 6;transform-box:fill-box;transform-origin:center;animation:kz-spin 26s linear infinite reverse}
.kz-mtext{fill:#bfeaf7;font-family:var(--mono);font-size:22px;letter-spacing:3px}
.kz-mtext-core{fill:#effcff;font-size:19px;letter-spacing:2px}

/* final */
.kz-final{position:relative;z-index:1;min-height:100svh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:100px 20px 40px;overflow:hidden}
.kz-final::before{content:"";position:absolute;inset:0;background:radial-gradient(ellipse at 50% 50%,rgba(20,70,150,.28),transparent 65%)}
.kz-final-rings{position:absolute;left:50%;top:50%;width:min(150vw,980px);aspect-ratio:1;transform:translate(-50%,-50%);opacity:.34}
.kz-final-inner{position:relative;z-index:2;max-width:900px}
.kz-final-title{font-size:clamp(1.9rem,7.4vw,4.8rem);font-weight:200;letter-spacing:.1em;line-height:1.16;color:#f2fdff;text-shadow:0 0 30px rgba(79,216,255,.55),0 0 90px rgba(47,134,255,.4)}
.kz-final-small{margin:26px 0 38px;font-family:var(--mono);font-size:.7rem;letter-spacing:.5em;padding-left:.5em;color:var(--c)}
.kz-foot{position:relative;z-index:2;margin-top:64px;font-family:var(--mono);font-size:.56rem;letter-spacing:.2em;color:rgba(123,152,171,.6)}

/* responsive */
@media (min-width:600px){
  .kz-dock{grid-template-columns:1fr 1fr;max-width:760px}
  .kz-tele{grid-column:1 / -1}
  .kz-markets{grid-template-columns:1fr 1fr}
  .kz-sig-body{grid-template-columns:1fr auto;gap:48px}
  .kz-nav{padding:22px 32px}
  .kz-tag{font-size:.66rem}
}
@media (min-width:760px){
  .kz-links{order:0;width:auto;gap:30px}
  .kz-nav{flex-wrap:nowrap}
  .kz-status{order:3}
  .kz-nav .kz-links{margin-left:auto;margin-right:26px}
}
@media (min-width:1100px){
  .kz-markets{grid-template-columns:repeat(4,1fr)}
  .kz-dock{position:absolute;inset:0;max-width:none;margin:0;padding:0;display:block;pointer-events:none}
  .kz-dock > *{pointer-events:auto}
  .kz-panel{position:absolute;width:224px}
  .kz-panel.p1{left:1%;top:150px}
  .kz-panel.p2{right:1%;top:118px}
  .kz-panel.p3{left:3%;top:380px}
  .kz-tele{position:absolute;right:2%;top:340px;width:250px;grid-column:auto}
}
@media (max-width:420px){
  .kz-tag{font-size:.52rem;letter-spacing:.14em}
  .kz-btn{width:100%}
  .kz-actions{flex-direction:column;align-items:stretch;padding:0 4px}
  .kz-rung{grid-template-columns:44px 1fr auto;gap:8px;font-size:.6rem}
  .kz-mkt li{font-size:.6rem;letter-spacing:.14em}
}

/* keyframes */
@keyframes kz-spin{to{transform:rotate(360deg)}}
@keyframes kz-pulse{0%,100%{box-shadow:0 0 60px rgba(79,216,255,.3),0 0 140px rgba(47,134,255,.18),inset 0 0 40px rgba(79,216,255,.25);transform:scale(1)}
  50%{box-shadow:0 0 90px rgba(79,216,255,.5),0 0 190px rgba(47,134,255,.3),inset 0 0 56px rgba(79,216,255,.4);transform:scale(1.025)}}
@keyframes kz-breathe{0%,100%{opacity:.75;transform:scale(1)}50%{opacity:1;transform:scale(1.06)}}
@keyframes kz-blink{0%,100%{opacity:1}50%{opacity:.35}}
@keyframes kz-float{from{transform:translateY(-6px)}to{transform:translateY(8px)}}
@keyframes kz-bar{0%{transform:translateX(-120%)}100%{transform:translateX(320%)}}
@keyframes kz-meter{0%,100%{width:96%}50%{width:99%}}
@keyframes kz-rise{0%{transform:translate3d(0,0,0);opacity:0}10%{opacity:.8}90%{opacity:.5}100%{transform:translate3d(var(--dx,0),-110vh,0);opacity:0}}
@keyframes kz-scan{to{transform:translateY(160vh)}}
@keyframes kz-grid{to{background-position:0 56px,56px 0}}
@keyframes kz-ring{0%{transform:scale(.7);opacity:.8}100%{transform:scale(1.25);opacity:0}}
@keyframes kz-caret{50%{opacity:0}}
@keyframes kz-flow{to{stroke-dashoffset:-48}}
@keyframes kz-draw{from{stroke-dashoffset:263.9}}
@keyframes kz-ladder{from{transform:translateY(0)}to{transform:translateY(190px)}}
@keyframes kz-l1{0%,3%{opacity:0;transform:translateX(-8px)}8%,90%{opacity:1;transform:none}96%,100%{opacity:0}}
@keyframes kz-l2{0%,24%{opacity:0;transform:translateX(-8px)}30%,90%{opacity:1;transform:none}96%,100%{opacity:0}}
@keyframes kz-l3{0%,46%{opacity:0;transform:translateX(-8px)}52%,90%{opacity:1;transform:none}96%,100%{opacity:0}}

@media (prefers-reduced-motion:reduce){
  .kz *,.kz *::before,.kz *::after{animation:none !important;transition:none !important}
  .kz-particle{display:none}
}
`;
