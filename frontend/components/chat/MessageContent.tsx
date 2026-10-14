"use client";

import React, { useState } from "react";

type Props = { content: string; isUser?: boolean };

type PyodideRuntime = {
  runPythonAsync: (source: string) => Promise<unknown>;
  setStdout: (options: { batched: (text: string) => void }) => void;
  setStderr: (options: { batched: (text: string) => void }) => void;
};


function safeImageUrl(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function InlineText({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\(https?:\/\/[^\s)]+\))/g);
  return <>{parts.map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i} className="rounded bg-slate-800/80 px-1.5 py-0.5 font-mono text-[0.92em] text-cyan-100">{part.slice(1, -1)}</code>;
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i} className="font-semibold text-slate-100">{part.slice(2, -2)}</strong>;
    if (part.startsWith("*") && part.endsWith("*")) return <em key={i}>{part.slice(1, -1)}</em>;
    const link = part.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
    if (link) return <a key={i} href={link[2]} target="_blank" rel="noopener noreferrer" className="text-cyan-300 underline underline-offset-2">{link[1]}</a>;
    return <React.Fragment key={i}>{part}</React.Fragment>;
  })}</>;
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState("");
  const [preview, setPreview] = useState(false);
  const copy = async () => {
    try { await navigator.clipboard.writeText(code); setCopied(true); window.setTimeout(() => setCopied(false), 1500); } catch { setOutput("Copy failed. Check browser clipboard permissions."); }
  };
  const normalizedLanguage = language.toLowerCase();
  const isPython = ["python", "py"].includes(normalizedLanguage);
  const isHtml = ["html", "htm"].includes(normalizedLanguage);
  const extMap: Record<string, string> = { tsx: "tsx", typescript: "ts", ts: "ts", jsx: "jsx", javascript: "js", js: "js", python: "py", py: "py", html: "html", css: "css", json: "json", bash: "sh", sh: "sh", sql: "sql", yaml: "yml", yml: "yml", markdown: "md", md: "md", java: "java", go: "go", rust: "rs", c: "c", cpp: "cpp" };
  const ext = extMap[normalizedLanguage] || "txt";
  const download = () => {
    const blob = new Blob([code], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `king-zarry-code.${ext}`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };
  const runPython = async () => {
    if (running) return;
    setRunning(true); setOutput("Starting Python WebAssembly runtime…");
    try {
      const w = window as Window & { loadPyodide?: (options: { indexURL: string }) => Promise<PyodideRuntime>; __kzPyodide?: PyodideRuntime };
      const loadRuntime = async () => {
        if (w.__kzPyodide) return w.__kzPyodide;
        if (!w.loadPyodide) {
          await new Promise<void>((resolve, reject) => {
            const existing = document.querySelector<HTMLScriptElement>('script[data-kz-pyodide="true"]');
            const script = existing || document.createElement("script");
            script.src = "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js";
            script.dataset.kzPyodide = "true";
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Could not load Python runtime from CDN."));
            if (!existing) document.head.appendChild(script);
          });
        }
        if (!w.loadPyodide) throw new Error("Python runtime did not initialize.");
        w.__kzPyodide = await w.loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.27.7/full/" });
        return w.__kzPyodide;
      };
      const runtime = await loadRuntime();
      const logs: string[] = [];
      runtime.setStdout({ batched: (text: string) => logs.push(text) });
      runtime.setStderr({ batched: (text: string) => logs.push(text) });
      const result = await runtime.runPythonAsync(code);
      if (result !== undefined && result !== null) logs.push(String(result));
      setOutput(logs.join("\n") || "Finished successfully (no output).");
    } catch (error) {
      setOutput(`Execution error: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setRunning(false);
    }
  };
  return <section className="my-3 min-w-0 overflow-hidden rounded-xl border border-cyan-500/20 bg-[#050b12]">
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 bg-white/[0.035] px-3 py-2">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-cyan-100/60">{language || "code"}</span>
      <div className="flex flex-wrap gap-1">
        <button type="button" onClick={() => void copy()} className="rounded-md px-2 py-1 text-xs text-cyan-100/75 hover:bg-white/10">{copied ? "Copied" : "Copy code"}</button>
        {isPython ? <button type="button" disabled={running} onClick={() => void runPython()} className="rounded-md bg-sky-700 px-2 py-1 text-xs text-white hover:bg-sky-600 disabled:opacity-50">{running ? "Running…" : "▶ Run Python"}</button> : null}
        {isHtml ? <button type="button" onClick={() => setPreview((value) => !value)} className="rounded-md px-2 py-1 text-xs text-cyan-100/75 hover:bg-white/10">{preview ? "Hide preview" : "Preview HTML"}</button> : null}
        <button type="button" onClick={download} className="rounded-md px-2 py-1 text-xs text-cyan-100/75 hover:bg-white/10">Download .{ext}</button>
      </div>
    </div>
    <pre className="max-h-[min(65vh,720px)] overflow-auto p-4 text-[12px] leading-5 text-slate-100 sm:text-[13px]"><code>{code}</code></pre>
    {preview && isHtml ? <iframe title="HTML code preview" sandbox="allow-scripts" srcDoc={code} className="h-72 w-full border-t border-white/10 bg-white" /> : null}
    {output ? <div className="border-t border-white/10"><div className="bg-white/[0.035] px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-cyan-100/60">Python output</div><pre role="status" aria-live="polite" className="max-h-72 overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-xs text-emerald-200">{output}</pre></div> : null}
  </section>;
}

export default function MessageContent({ content, isUser = false }: Props) {
  if (isUser) return <div className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{content}</div>;
  const blocks = content.split(/```/);
  return <div className="min-w-0 max-w-full break-words [overflow-wrap:anywhere]">
    {blocks.map((block, index) => {
      if (index % 2 === 1) {
        const newline = block.indexOf("\n");
        const first = newline < 0 ? block : block.slice(0, newline);
        const language = /^[a-zA-Z0-9_+#.-]{1,24}$/.test(first.trim()) ? first.trim() : "";
        const code = language ? block.slice(newline + 1) : block;
        return <CodeBlock key={index} code={code.replace(/\n?\s*$/, "")} language={language} />;
      }
      const lines = block.split("\n");
      const elements: React.ReactNode[] = [];
      let paragraph: string[] = [];
      let list: string[] = [];
      const flushParagraph = () => { if (paragraph.length) { elements.push(<p key={`p-${elements.length}`} className="my-2 whitespace-pre-wrap"><InlineText text={paragraph.join("\n")} /></p>); paragraph = []; } };
      const flushList = () => { if (list.length) { elements.push(<ul key={`ul-${elements.length}`} className="my-2 list-disc space-y-1 pl-6">{list.map((item, i) => <li key={i}><InlineText text={item} /></li>)}</ul>); list = []; } };
      lines.forEach((line) => {
        const imageMatch = line.match(/^!\[([^\]]*)\]\((https?:\/\/[^\s)]+)\)\s*$/);
        if (imageMatch) {
          flushParagraph(); flushList();
          const url = safeImageUrl(imageMatch[2]);
          if (url) elements.push(<figure key={`img-${elements.length}`} className="my-3"><img src={url} alt={imageMatch[1] || "Generated image"} loading="lazy" className="max-h-[70vh] max-w-full rounded-xl border border-white/10 object-contain" /><figcaption className="mt-1 text-xs text-slate-400">{imageMatch[1] || "Generated image"} · <a href={url} target="_blank" rel="noopener noreferrer" className="text-cyan-300 underline">Open image</a></figcaption></figure>);
          else elements.push(<p key={`badimg-${elements.length}`} className="my-2 text-sm text-slate-400">Image URL could not be displayed securely.</p>);
          return;
        }
        const heading = line.match(/^(#{1,3})\s+(.+)$/);
        const item = line.match(/^\s*[-*+]\s+(.+)$/);
        if (!line.trim()) { flushParagraph(); flushList(); return; }
        if (heading) { flushParagraph(); flushList(); elements.push(React.createElement(heading[1].length === 1 ? "h2" : heading[1].length === 2 ? "h3" : "h4", { key: `h-${elements.length}`, className: "my-3 font-semibold text-slate-100" }, <InlineText text={heading[2]} />)); return; }
        if (item) { flushParagraph(); list.push(item[1]); return; }
        flushList(); paragraph.push(line);
      });
      flushParagraph(); flushList();
      return <React.Fragment key={index}>{elements}</React.Fragment>;
    })}
  </div>;
}
