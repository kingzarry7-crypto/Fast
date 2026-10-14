"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";

type Skill = {
  id: string;
  name: string;
  description: string;
  icon: string;
  task_types: string[];
  tools: string[];
  execution: string;
  approval: string;
  available: boolean;
};

type RunResult = {
  status?: string;
  detail?: string;
  skill?: { id: string; name: string };
  agent?: Record<string, unknown>;
};

const FALLBACK_SKILLS: Skill[] = [
  { id: "coding", name: "Coding & App Building", description: "Plan and create applications, APIs, components, and code changes.", icon: "⌘", task_types: ["engineering", "website_build"], tools: ["repository_files", "agent_workflow"], execution: "Isolated runner required for full project execution.", approval: "Review changes before merging or deploying.", available: false },
  { id: "web", name: "Web Research", description: "Research current information and summarize evidence with sources.", icon: "◎", task_types: ["research", "browser"], tools: ["configured_web_search", "browser_operator"], execution: "Existing research workflow.", approval: "Authenticated sessions and consequential actions require approval.", available: true },
  { id: "images", name: "Images & Media", description: "Prepare image or video generation/editing requests using configured providers.", icon: "▧", task_types: ["image_generation", "media_editing"], tools: ["configured_media_providers"], execution: "Depends on the media provider being configured.", approval: "Confirm paid or external publishing actions.", available: true },
  { id: "github", name: "GitHub & Delivery", description: "Inspect repository files, prepare code changes, and check CI/deployment evidence.", icon: "⑂", task_types: ["github", "engineering", "deployment"], tools: ["github_connector_when_authorized", "workflow_engine"], execution: "Repository actions are permission-gated.", approval: "Review before merge, release, or production deployment.", available: true },
  { id: "testing", name: "Testing & Debugging", description: "Create test plans, diagnose errors, and report verified test results.", icon: "✓", task_types: ["testing", "debugging"], tools: ["configured_test_runner", "workflow_engine"], execution: "Isolated runner required for untrusted code.", approval: "Tests are only reported as passing when evidence is available.", available: true },
  { id: "data", name: "Data & Machine Learning", description: "Analyze datasets, validate features, train models, and evaluate results.", icon: "▥", task_types: ["data_analysis", "machine_learning"], tools: ["python_runner_for_supported_snippets", "configured_data_tools"], execution: "Browser Python for supported snippets; isolated runner for full jobs.", approval: "Separate measured results from estimates and protect uploaded data.", available: true },
];

const TASK_HINTS: Record<string, string> = {
  coding: "Describe the app, feature, or code change you want built.",
  web: "Describe the question you want researched and what evidence you need.",
  images: "Describe the image or video you want created or edited.",
  github: "Describe the repository task. Include the repository or file when relevant.",
  testing: "Describe the failure, test, or behaviour you want verified.",
  data: "Describe the dataset, analysis, or model evaluation you need.",
};

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>(FALLBACK_SKILLS);
  const [selected, setSelected] = useState("coding");
  const [goal, setGoal] = useState("");
  const [loadingSkills, setLoadingSkills] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<RunResult | null>(null);

  const loadSkills = useCallback(async () => {
    try {
      const response = await fetch("/api/skills", { credentials: "include", headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(response.status === 401 ? "Please sign in again to load your skills." : "Skill catalogue is temporarily unavailable.");
      const data = await response.json();
      if (Array.isArray(data.skills) && data.skills.length) setSkills(data.skills);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load skills. Showing the built-in catalogue.");
    } finally {
      setLoadingSkills(false);
    }
  }, []);

  useEffect(() => { void loadSkills(); }, [loadSkills]);

  const runTask = async () => {
    if (!goal.trim() || running) return;
    setRunning(true); setError(""); setResult(null);
    try {
      const response = await fetch("/api/skills/run", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ skill_id: selected, goal: goal.trim(), run_now: true }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || data.message || `Task failed (HTTP ${response.status}).`);
      setResult(data as RunResult);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start this task.");
    } finally {
      setRunning(false);
    }
  };

  const active = skills.find((skill) => skill.id === selected) || skills[0];

  return (
    <ProtectedRoute>
      <main className="min-h-[100dvh] bg-[#05080f] px-4 py-6 text-slate-100 sm:px-8 sm:py-10">
        <div className="mx-auto max-w-6xl">
          <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
            <div>
              <Link href="/dashboard" className="text-xs text-cyan-300 hover:text-cyan-100">← Back to dashboard</Link>
              <p className="mt-4 text-[10px] font-semibold uppercase tracking-[0.28em] text-cyan-300/70">King Zarry AI · Capability workspace</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">Build & Skills</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Choose a skill and submit a task through the authenticated agent workflow. A skill is not marked ready until its required integrations are verified.</p>
            </div>
            <div className="rounded-xl border border-cyan-400/20 bg-cyan-400/[0.06] px-4 py-3 text-xs text-cyan-100/80">
              {loadingSkills ? "Checking skills…" : `${skills.filter((skill) => skill.available).length} verified ready · ${skills.length} defined`}
            </div>
          </header>

          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {skills.map((skill) => (
              <button key={skill.id} type="button" onClick={() => { setSelected(skill.id); setError(""); setResult(null); }}
                className={"rounded-2xl border p-4 text-left transition " + (selected === skill.id ? "border-cyan-300/50 bg-cyan-300/[0.09] shadow-[0_0_28px_rgba(34,211,238,0.06)]" : "border-white/10 bg-white/[0.025] hover:border-white/20 hover:bg-white/[0.045]")}>
                <div className="flex items-start gap-3">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-300/20 bg-cyan-300/[0.08] text-lg text-cyan-200">{skill.icon || "✦"}</span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold text-white">{skill.name}</h2><span className={"rounded-full border px-2 py-0.5 text-[9px] " + (skill.available ? "border-emerald-400/30 text-emerald-200" : "border-amber-400/30 text-amber-200")}>{skill.available ? "Verified ready" : "Not verified"}</span></div>
                    <p className="mt-1 text-xs leading-5 text-slate-400">{skill.description}</p>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-1.5">
                  {skill.task_types.slice(0, 3).map((type) => <span key={type} className="rounded-full border border-white/10 px-2 py-1 text-[10px] text-slate-400">{type.replaceAll("_", " ")}</span>)}
                </div>
              </button>
            ))}
          </section>

          {active && <section className="mt-6 grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
            <div className="rounded-2xl border border-white/10 bg-[#0a111b] p-4 sm:p-6">
              <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-300/70">Start a task</p>
              <h2 className="mt-2 text-xl font-semibold">{active.name}</h2>
              <label htmlFor="skill-goal" className="mt-5 block text-xs font-medium text-slate-300">What should King Zarry AI do?</label>
              <textarea id="skill-goal" value={goal} onChange={(e) => setGoal(e.target.value)} maxLength={4000} rows={5}
                placeholder={TASK_HINTS[selected] || "Describe the outcome you want…"}
                className="mt-2 w-full resize-y rounded-xl border border-white/10 bg-[#050a12] p-3 text-sm leading-6 text-white outline-none placeholder:text-slate-600 focus:border-cyan-300/40" />
              <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500"><span>Tasks are routed through the existing agent.</span><span>{goal.length}/4000</span></div>
              <button type="button" onClick={() => void runTask()} disabled={!goal.trim() || running}
                className="mt-4 inline-flex items-center gap-2 rounded-full bg-cyan-300 px-5 py-2.5 text-sm font-semibold text-[#041019] transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-50">
                {running ? "Starting task…" : "✦ Start task"}
              </button>
              {error && <p role="alert" className="mt-4 rounded-xl border border-red-400/20 bg-red-400/[0.06] p-3 text-sm text-red-200">{error}</p>}
              {result && <div className="mt-5 rounded-xl border border-cyan-300/20 bg-black/20 p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-cyan-200">Agent response</p>
                <p className="mt-1 text-sm text-slate-300">{result.skill?.name || active.name} · {String(result.agent?.status || result.status || "submitted")}</p>
                <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-black/30 p-3 text-xs leading-5 text-slate-300">{JSON.stringify(result.agent || result, null, 2)}</pre>
                <p className="mt-3 text-xs leading-5 text-slate-500">Review any approval request in the agent workflow before consequential actions. A submitted workflow is not proof that its task completed.</p>
              </div>}
            </div>

            <aside className="h-fit rounded-2xl border border-white/10 bg-[#0a111b] p-4 sm:p-5">
              <h3 className="font-semibold text-white">Skill policy</h3>
              <p className="mt-3 text-xs leading-5 text-slate-400">{active.approval}</p>
              <div className="my-4 h-px bg-white/10" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Execution mode</h3>
              <p className="mt-2 break-words text-xs leading-5 text-slate-400">{active.execution}</p>
              <div className="my-4 h-px bg-white/10" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Tools declared</h3>
              <div className="mt-2 flex flex-wrap gap-1.5">{active.tools.map((tool) => <span key={tool} className="rounded-md bg-white/[0.05] px-2 py-1 text-[10px] text-slate-400">{tool.replaceAll("_", " ")}</span>)}</div>
              <p className="mt-4 text-[10px] leading-5 text-slate-500">A listed capability does not guarantee a provider is connected. King Zarry AI must verify access and report missing tools instead of pretending an action succeeded.</p>
            </aside>
          </section>}
        </div>
      </main>
    </ProtectedRoute>
  );
}
