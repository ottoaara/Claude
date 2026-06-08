"use client";

import { useEffect, useState, useRef } from "react";
import { api, APIError } from "../lib/api";

interface Props {
  jobId: string;
  companyName: string;
  onComplete: (result: any) => void;
}

interface JobStatus {
  job_id: string;
  status: string;
  company_name: string;
  started_at: string;
  completed_at?: string;
  progress: {
    completed_steps?: string[];
    total_steps?: number;
  };
  result?: any;
  error?: string;
}

// ─── Step definitions with agent metadata ────────────────────────────────────
const STEPS = [
  {
    key: "company_info",
    label: "Company Profile",
    agent: "WebScraperAgent",
    description: "Scraping company website · Extracting business profile via LLM",
    tools: ["BeautifulSoup", "__LLM__"],
  },
  {
    key: "financials",
    label: "SEC Filings",
    agent: "EdgarAgent",
    description: "Downloading 10-K & 10-Q from SEC EDGAR · Parsing revenue, assets, cash flow",
    tools: ["sec-edgar-downloader", "XBRL Parser"],
  },
  {
    key: "news",
    label: "News & Sentiment",
    agent: "NewsAgent + NewsClassifier",
    description: "Searching recent news · Classifying sentiment, severity & material events",
    tools: ["DuckDuckGo", "__LLM__"],
  },
  {
    key: "products",
    label: "Product Portfolio",
    agent: "ProductAgent",
    description: "Generating banking product portfolio based on company profile & sector",
    tools: ["__LLM__"],
  },
  {
    key: "industry",
    label: "Industry & Peers",
    agent: "IndustryAgent",
    description: "NAICS classification · Discovering peer companies with tickers",
    tools: ["DuckDuckGo", "__LLM__"],
  },
  {
    key: "peer_financials",
    label: "Peer Financials",
    agent: "EdgarAgent (×peers)",
    description: "Fetching SEC filings for each peer company · Building comparison dataset",
    tools: ["sec-edgar-downloader", "Ticker Normaliser"],
  },
  {
    key: "officer_research",
    label: "Officer Intelligence",
    agent: "OfficerAgent",
    description: "Multi-source discovery: website · SEC proxy · Wikipedia · press releases",
    tools: ["DuckDuckGo", "BeautifulSoup", "__LLM__"],
  },
  {
    key: "temporal_scoring",
    label: "Temporal Weighting",
    agent: "TemporalDimension",
    description: "Applying freshness decay curves · Scoring relevance · Pruning stale data",
    tools: ["Decay Engine", "Relevance Scorer"],
  },
  {
    key: "graph_populated",
    label: "Knowledge Graph",
    agent: "Neo4j + LLM",
    description: "Storing all dimensions as graph nodes · Generating AI executive summary",
    tools: ["Neo4j 4.x", "__LLM__"],
  },
];

// Wells Fargo: red = active, gold = done, gray = pending
const WF = {
  active: { border: "border-[#D71E28]", bg: "bg-white",        text: "text-[#D71E28]", badge: "bg-red-50 text-[#D71E28]",         ring: "ring-[#D71E28]", dot: "bg-[#D71E28]"  },
  done:   { border: "border-[#FFCD41]", bg: "bg-[#FFFBEA]",    text: "text-[#7A5C00]", badge: "bg-[#FFCD41] text-[#7A5C00]",     ring: "ring-[#FFCD41]", dot: "bg-[#FFCD41]"  },
  pending:{ border: "border-gray-200",  bg: "bg-white",         text: "text-gray-400",  badge: "bg-gray-100 text-gray-400",       ring: "ring-gray-200",  dot: "bg-gray-300"   },
};

// What each agent contributes — shown in the facts panel as steps complete
const STEP_SIGNALS: Record<string, { label: string; detail: string }> = {
  company_info:     { label: "Company Profile",    detail: "Website · business model · HQ · headcount" },
  financials:       { label: "SEC Filings",        detail: "10-K · 10-Q · revenue · debt · ratios" },
  news:             { label: "News & Sentiment",   detail: "Headlines · sentiment · material events" },
  products:         { label: "Product Portfolio",  detail: "Banking product surface area mapped" },
  industry:         { label: "Industry & Peers",   detail: "NAICS code · 3–5 peer companies" },
  peer_financials:  { label: "Peer Benchmarks",    detail: "Peer revenue · margin · debt benchmarks" },
  officer_research: { label: "Officer Intelligence",detail: "C-suite · board · education · risk flags" },
  temporal_scoring: { label: "Freshness Scores",   detail: "Decay curves · relevance scores applied" },
  graph_populated:  { label: "Knowledge Graph",    detail: "All nodes stored · AI summary generated" },
};

// Rotating "thinking" messages shown while a step is active
const THINKING: Record<string, string[]> = {
  company_info:     ["Fetching company homepage…", "Parsing HTML structure…", "Extracting business profile…", "Identifying sector and HQ…"],
  financials:       ["Connecting to SEC EDGAR…", "Downloading latest 10-K…", "Parsing XBRL financials…", "Extracting revenue & assets…"],
  news:             ["Searching recent headlines…", "Filtering by relevance…", "Classifying sentiment…", "Flagging material events…"],
  products:         ["Analysing company sector…", "Mapping banking products…", "Scoring revenue impact…", "Finalising portfolio…"],
  industry:         ["Identifying NAICS code…", "Finding peer companies…", "Sourcing peer tickers…", "Benchmarking industry position…"],
  peer_financials:  ["Normalising peer tickers…", "Fetching peer 10-Ks…", "Building comparison dataset…", "Calculating peer metrics…"],
  officer_research: ["Scraping leadership page…", "Searching SEC proxy filings…", "Checking Wikipedia…", "Profiling executives…", "Flagging risk factors…"],
  temporal_scoring: ["Applying decay curves…", "Scoring news freshness…", "Weighting filing dates…", "Pruning stale data…"],
  graph_populated:  ["Merging company node…", "Storing financial edges…", "Linking officer profiles…", "Generating AI summary…"],
};

function useTickingMessage(messages: string[], active: boolean, intervalMs = 1800) {
  const [idx, setIdx] = useState(0);
  const ref = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!active) { setIdx(0); return; }
    ref.current = setInterval(() => setIdx(i => (i + 1) % messages.length), intervalMs);
    return () => { if (ref.current) clearInterval(ref.current); };
  }, [active, messages.length, intervalMs]);

  return messages[idx];
}

function ActiveMessage({ stepKey, messages }: { stepKey: string; messages: string[] }) {
  const msg = useTickingMessage(messages, true);
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-mono text-gray-500 animate-pulse">
      <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#D71E28] animate-ping" />
      {msg}
    </span>
  );
}

function ElapsedTimer({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const start = new Date(startedAt).getTime();
    const t = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(t);
  }, [startedAt]);
  const m = Math.floor(elapsed / 60);
  const s = elapsed % 60;
  return <span className="font-mono text-sm text-[#666666]">{m}:{s.toString().padStart(2, "0")}</span>;
}

export default function ResearchProgress({ jobId, companyName, onComplete }: Props) {
  const [status, setStatus]     = useState<JobStatus | null>(null);
  const [error, setError]       = useState("");
  const [llmLabel, setLlmLabel] = useState("LLM");
  const [wikiData, setWikiData] = useState<{ extract: string; description?: string; thumbnail?: string } | null>(null);
  const [wikiLoading, setWikiLoading] = useState(true);
  const [wikiSentenceIdx, setWikiSentenceIdx] = useState(0);

  // Fetch LLM label once on mount
  useEffect(() => {
    api.healthCheck().then(h => {
      if (h.llm_label) setLlmLabel(h.llm_label);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await api.getResearchStatus(jobId);
        setStatus(data);
        if (data.status === "completed") setTimeout(() => onComplete(data.result || {}), 1800);
        else if (data.status === "failed") setError(data.error || "Research failed");
      } catch (err) {
        setError(err instanceof APIError ? err.message : err instanceof Error ? err.message : "Unknown error");
      }
    };
    poll();
    const iv = setInterval(poll, 2000);
    return () => clearInterval(iv);
  }, [jobId, onComplete]);

  // Fetch Wikipedia summary for the company
  useEffect(() => {
    const fetchWiki = async () => {
      try {
        const r = await fetch(
          `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(companyName)}`
        );
        if (r.ok) {
          const d = await r.json();
          setWikiData({
            extract: d.extract || "",
            description: d.description,
            thumbnail: d.thumbnail?.source,
          });
        }
      } catch {}
      setWikiLoading(false);
    };
    fetchWiki();
  }, [companyName]);

  // Rotate through Wikipedia sentences every 5s
  useEffect(() => {
    if (!wikiData?.extract) return;
    const sentences = wikiData.extract
      .replace(/\([^)]*\)/g, "")
      .split(/(?<=[.!?])\s+/)
      .filter(s => s.length > 40)
      .slice(0, 8);
    if (sentences.length < 2) return;
    const t = setInterval(() => setWikiSentenceIdx(i => (i + 1) % sentences.length), 5000);
    return () => clearInterval(t);
  }, [wikiData]);

  const completedSteps = [...new Set(status?.progress?.completed_steps || [])];
  const activeIndex    = status?.status === "running" ? completedSteps.length : -1;
  const progressPct    = Math.min(100, (completedSteps.length / STEPS.length) * 100);
  const isComplete     = status?.status === "completed";
  const isFailed       = status?.status === "failed";

  // Sentences from Wikipedia extract for the rotating fact card
  const wikiSentences = wikiData?.extract
    .replace(/\([^)]*\)/g, "")
    .split(/(?<=[.!?])\s+/)
    .filter(s => s.length > 40)
    .slice(0, 8) ?? [];

  return (
    <div className="max-w-5xl mx-auto px-4">

      {/* ── Header card ─────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl shadow-lg border-2 border-gray-200 overflow-hidden mb-6">

        {/* Red top bar */}
        <div className="h-1.5 bg-[#D71E28]" />

        <div className="p-8">
          <div className="flex items-start justify-between gap-4 mb-6">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-[#D71E28] mb-1">
                Context Fabric · AI Research Pipeline
              </p>
              <h2 className="text-3xl font-black text-[#333333]">{companyName}</h2>
              <p className="text-[#666666] mt-1 text-sm">
                {isComplete ? "All dimensions complete — loading dashboard…"
                  : isFailed ? "Pipeline encountered an error"
                  : `Running ${STEPS.length}-agent LangGraph workflow · ${llmLabel}`}
              </p>
            </div>
            <div className="text-right flex-shrink-0">
              {status?.started_at && !isComplete && !isFailed && (
                <div className="text-xs text-gray-400 mb-1 uppercase tracking-wide">Elapsed</div>
              )}
              {status?.started_at && !isComplete && !isFailed && (
                <ElapsedTimer startedAt={status.started_at} />
              )}
              {isComplete && (
                <span className="text-green-600 font-black text-lg">Done</span>
              )}
            </div>
          </div>

          {/* Progress bar */}
          <div className="mb-2 flex justify-between text-xs font-bold text-[#666666] uppercase tracking-wide">
            <span>{completedSteps.length} of {STEPS.length} steps</span>
            <span>{Math.round(progressPct)}%</span>
          </div>
          <div className="h-3 bg-gray-100 rounded-full overflow-hidden border border-gray-200">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${isComplete ? "bg-green-500" : "bg-[#D71E28]"}`}
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {/* Agent pipeline overview dots */}
          <div className="mt-4 flex items-center gap-1 flex-wrap">
            {STEPS.map((step, i) => {
              const done   = completedSteps.includes(step.key);
              const active = i === activeIndex;
              const c      = done ? WF.done : active ? WF.active : WF.pending;
              return (
                <div key={step.key} className="flex items-center gap-1">
                  <div
                    title={step.agent}
                    className={`w-6 h-6 rounded flex items-center justify-center text-xs font-black transition-all duration-300 ${
                      done   ? `${c.dot} text-[#7A5C00] ring-2 ring-offset-1 ring-white shadow` :
                      active ? `${c.dot} text-white ring-2 ring-offset-1 ${c.ring} animate-pulse shadow-lg` :
                               "bg-gray-200 text-gray-400"
                    }`}
                  >
                    {done ? "" : i + 1}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className={`w-3 h-0.5 rounded ${done ? "bg-[#FFCD41]" : "bg-gray-200"}`} />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Two-column: Steps (left) + Facts (right) ─────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">

      {/* Step list ─ left 3 cols */}
      <div className="lg:col-span-3 space-y-2">
        {STEPS.map((step, index) => {
          const done   = completedSteps.includes(step.key);
          const active = index === activeIndex;
          const pending = !done && !active;
          const c = done ? WF.done : active ? WF.active : WF.pending;

          return (
            <div
              key={step.key}
              className={`rounded-none border-l-4 transition-all duration-400 overflow-hidden ${
                done   ? `${c.border} ${c.bg} shadow-sm` :
                active ? `${c.border} bg-white shadow-md ring-1 ${c.ring}` :
                         "border-gray-200 bg-white opacity-40"
              }`}
            >
              <div className="flex items-center gap-4 px-5 py-4">

                {/* Step number / check */}
                <div className={`w-10 h-10 rounded-sm flex items-center justify-center flex-shrink-0 font-black text-sm transition-all ${
                  done   ? "bg-[#FFCD41] text-[#7A5C00] shadow" :
                  active ? "bg-[#D71E28] text-white shadow-lg animate-pulse" :
                           "bg-gray-100 text-gray-400"
                }`}>
                  {done ? "" : index + 1}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className={`font-black text-sm ${c.text}`}>
                      {step.label}
                    </p>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${c.badge}`}>
                      {step.agent}
                    </span>
                  </div>

                  {/* Sub-text */}
                  {(done || active) && (
                    <div className="mt-1">
                      {active
                        ? <ActiveMessage stepKey={step.key} messages={THINKING[step.key] || [step.description]} />
                        : <p className="text-xs text-gray-500">{step.description}</p>
                      }
                    </div>
                  )}

                  {/* Tool chips — shown when active or done */}
                  {(done || active) && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {step.tools.map(t => {
                        const display = t === "__LLM__" ? llmLabel : t;
                        const isLlm   = t === "__LLM__";
                        return (
                          <span
                            key={t}
                            className={`text-xs font-mono px-2 py-0.5 rounded border ${
                              isLlm
                                ? "bg-[#D71E28] text-white border-[#D71E28]"
                                : "bg-gray-100 text-gray-500 border-gray-200"
                            }`}
                          >
                            {display}
                          </span>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Status badge */}
                <div className="flex-shrink-0 text-right">
                  {done && (
                    <span className="text-xs font-black px-3 py-1 rounded-full bg-[#FFCD41] text-[#7A5C00] uppercase tracking-wide">
                      Done
                    </span>
                  )}
                  {active && (
                    <span className="text-xs font-black px-3 py-1 rounded-full bg-[#D71E28] text-white uppercase tracking-wide animate-pulse">
                      ● Running
                    </span>
                  )}
                  {pending && (
                    <span className="text-xs font-bold px-3 py-1 rounded-full bg-gray-100 text-gray-400 uppercase tracking-wide">
                      Queued
                    </span>
                  )}
                </div>
              </div>

              {/* Active step: animated activity bar */}
              {active && (
                <div className="h-0.5 bg-gray-100 overflow-hidden">
                  <div className="h-full w-1/3 bg-[#D71E28] rounded"
                    style={{ animation: "slideRight 1.5s ease-in-out infinite" }} />
                </div>
              )}
            </div>
          );
        })}
      </div>{/* end step list col */}

      {/* Facts panel ─ right 2 cols */}
      <div className="lg:col-span-2 space-y-4 lg:sticky lg:top-4">

        {/* Wikipedia company snapshot */}
        <div className="bg-white rounded-xl border-2 border-gray-200 overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
            <span className="text-[10px] font-black uppercase tracking-widest text-[#D71E28]">Company Snapshot</span>
            {wikiData && <span className="text-[10px] text-gray-400 ml-auto">via Wikipedia</span>}
          </div>
          {wikiLoading ? (
            <div className="p-4 space-y-2 animate-pulse">
              <div className="h-3 bg-gray-100 rounded w-3/4" />
              <div className="h-3 bg-gray-100 rounded w-full" />
              <div className="h-3 bg-gray-100 rounded w-5/6" />
              <div className="h-3 bg-gray-100 rounded w-2/3" />
            </div>
          ) : wikiData ? (
            <div>
              {wikiData.thumbnail && (
                <div className="h-32 overflow-hidden">
                  <img
                    src={wikiData.thumbnail}
                    alt={companyName}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="p-4">
                {wikiData.description && (
                  <p className="text-[10px] font-bold uppercase tracking-wide text-[#888] mb-3">
                    {wikiData.description}
                  </p>
                )}
                {wikiSentences.length > 0 && (
                  <p
                    key={wikiSentenceIdx}
                    className="text-xs text-[#444] leading-relaxed"
                    style={{ animation: "wfFadeIn 0.7s ease" }}
                  >
                    {wikiSentences[wikiSentenceIdx]}
                  </p>
                )}
                {wikiSentences.length > 1 && (
                  <div className="flex gap-1 mt-3">
                    {wikiSentences.map((_, i) => (
                      <div
                        key={i}
                        className={`h-1 rounded-full transition-all duration-500 ${
                          i === wikiSentenceIdx ? "w-5 bg-[#D71E28]" : "w-1.5 bg-gray-200"
                        }`}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="p-4 text-xs text-gray-400 italic">
              No public profile found for &ldquo;{companyName}&rdquo;
            </div>
          )}
        </div>

        {/* Intelligence collected so far */}
        <div className="bg-white rounded-xl border-2 border-gray-200 overflow-hidden shadow-sm">
          <div className="px-4 py-3 border-b border-gray-100">
            <span className="text-[10px] font-black uppercase tracking-widest text-[#D71E28]">Intelligence Collected</span>
          </div>
          <div className="p-4">
            {completedSteps.length === 0 && activeIndex < 0 ? (
              <p className="text-xs text-gray-400 italic">Agents are initialising…</p>
            ) : (
              <div className="space-y-2">
                {completedSteps.map((key) => {
                  const sig = STEP_SIGNALS[key];
                  if (!sig) return null;
                  return (
                    <div
                      key={key}
                      className="flex items-start gap-2 p-2 rounded-lg bg-[#FFFBEA] border border-[#FFCD41]/40"
                      style={{ animation: "wfSlideIn 0.4s ease" }}
                    >
                      <div className="w-2 h-2 rounded-full bg-[#FFCD41] mt-1.5 flex-shrink-0" />
                      <div>
                        <p className="text-xs font-black text-[#7A5C00]">{sig.label}</p>
                        <p className="text-[10px] text-[#AA8800] leading-tight">{sig.detail}</p>
                      </div>
                    </div>
                  );
                })}
                {activeIndex >= 0 && activeIndex < STEPS.length && (
                  <div
                    className="flex items-start gap-2 p-2 rounded-lg bg-red-50 border border-[#D71E28]/20"
                    style={{ animation: "wfSlideIn 0.3s ease" }}
                  >
                    <div className="w-2 h-2 rounded-full bg-[#D71E28] mt-1.5 flex-shrink-0 animate-pulse" />
                    <div>
                      <p className="text-xs font-black text-[#D71E28]">
                        {STEP_SIGNALS[STEPS[activeIndex].key]?.label ?? STEPS[activeIndex].label}
                      </p>
                      <p className="text-[10px] text-[#D71E28]/60 leading-tight">Analysing now…</p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        <p className="text-center text-[10px] text-gray-400 px-2 leading-relaxed">
          Full research typically takes <strong className="text-gray-500">2–4 minutes</strong>. The
          dashboard loads automatically when all agents complete.
        </p>

      </div>{/* end facts panel col */}

      </div>{/* end grid */}

      {/* ── Error ───────────────────────────────────────────────────────── */}
      {error && (
        <div className="mt-6 p-5 bg-red-50 border-2 border-red-400 rounded-xl text-red-700">
          <p className="font-black uppercase tracking-wide text-sm mb-1">Pipeline Error</p>
          <p className="text-sm font-mono">{error}</p>
        </div>
      )}

      {/* ── Complete ────────────────────────────────────────────────────── */}
      {isComplete && (
        <div className="mt-6 p-6 bg-green-50 border-2 border-green-500 rounded-2xl text-center shadow">
          <p className="text-2xl font-black text-green-700 mb-1">Intelligence Brief Ready</p>
          <p className="text-sm text-green-600">
            {STEPS.length} agents · {completedSteps.length} dimensions complete · Loading dashboard…
          </p>
        </div>
      )}

      <style>{`
        @keyframes slideRight {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
        @keyframes wfFadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes wfSlideIn {
          from { opacity: 0; transform: translateX(8px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}
