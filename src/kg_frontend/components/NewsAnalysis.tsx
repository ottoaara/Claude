"use client";

import { useEffect, useState } from "react";
import { api, APIError } from "../lib/api";
import StockSparkline from "./StockSparkline";

interface NewsItem {
  title: string;
  summary?: string;
  url?: string;
  date?: string;
  sentiment?: "positive" | "neutral" | "negative";
  severity?: "high" | "medium" | "low";
  event_types?: string[];
  is_material?: boolean;
  key_facts?: string[];
}

interface NewsAnalysis {
  overall_sentiment?: string;
  risk_level?: string;
  key_concerns?: string[];
  positive_signals?: string[];
  material_events?: string[];
  summary?: string;
}

interface Props {
  companyName: string;
  ticker?: string;
  newsWindowDays?: number;
  onWindowChange?: (w: { fin_window: number; news_window: number; prod_window: number }) => void;
}

function SentimentBadge({ sentiment }: { sentiment?: string }) {
  const map: Record<string, string> = {
    positive: "bg-green-100 text-green-800 border-green-300",
    negative: "bg-red-100 text-red-800 border-red-300",
    neutral:  "bg-gray-100 text-gray-700 border-gray-300",
  };
  const cls = map[sentiment ?? "neutral"] ?? map.neutral;
  return (
    <span className={`px-2 py-0.5 text-xs font-bold rounded border uppercase tracking-wide ${cls}`}>
      {sentiment ?? "neutral"}
    </span>
  );
}

function SeverityBadge({ severity }: { severity?: string }) {
  const map: Record<string, string> = {
    high:   "bg-red-600 text-white",
    medium: "bg-yellow-500 text-white",
    low:    "bg-gray-400 text-white",
  };
  const cls = map[severity ?? "low"] ?? map.low;
  return (
    <span className={`px-2 py-0.5 text-xs font-bold rounded uppercase tracking-wide ${cls}`}>
      {severity ?? "low"}
    </span>
  );
}

function RiskLevel({ level }: { level?: string }) {
  const map: Record<string, string> = {
    high:   "text-red-600 bg-red-50 border-red-300",
    medium: "text-yellow-700 bg-yellow-50 border-yellow-300",
    low:    "text-green-700 bg-green-50 border-green-300",
  };
  const cls = map[level ?? "low"] ?? map.low;
  return (
    <span className={`px-3 py-1 text-sm font-bold rounded border uppercase tracking-wide ${cls}`}>
      {level ?? "low"} Risk
    </span>
  );
}

export default function NewsAnalysis({ companyName, ticker, newsWindowDays = 90, onWindowChange }: Props) {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [analysis, setAnalysis] = useState<NewsAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sentimentFilter, setSentimentFilter] = useState<"all" | "material" | "negative">("all");
  const [minSeverity, setMinSeverity] = useState<"all" | "medium" | "high">("all");
  const [stockData, setStockData] = useState<Record<string, any>>({});
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [windows, setWindows] = useState({ fin_window: 365, news_window: newsWindowDays, prod_window: 730 });

  const handleWindowChange = (key: keyof typeof windows, value: number) => {
    const updated = { ...windows, [key]: value };
    setWindows(updated);
    onWindowChange?.(updated);
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const data = await api.getCompanyGraph(companyName);
        const items: NewsItem[] = data.news || [];
        setNewsItems(items);
        setAnalysis(data.news_analysis || null);

        // Batch-fetch stock prices for all article dates if ticker is known
        const resolvedTicker = ticker || data.company?.ticker;
        if (resolvedTicker && items.length > 0) {
          const dates = [...new Set(
            items.map((n) => n.date).filter((d): d is string => !!d && /^\d{4}-\d{2}-\d{2}$/.test(d))
          )];
          if (dates.length > 0) {
            try {
              const prices = await api.getStockAroundDates(resolvedTicker, dates);
              setStockData(prices);
            } catch {
              // Stock data is best-effort; don't block news display
            }
          }
        }
      } catch (err) {
        if (err instanceof APIError) {
          setError(err.message);
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [companyName, ticker]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-12 text-center border-2 border-gray-200">
        <div className="inline-block w-12 h-12 border-4 border-[#D71E28] border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-[#666666] font-semibold">Loading news analysis...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-2 border-red-300 rounded p-8 text-red-700">
        <p className="font-bold mb-2 uppercase tracking-wide text-sm">Error:</p>
        <p>{error}</p>
      </div>
    );
  }

  const severityRank = { high: 3, medium: 2, low: 1 };
  const minSeverityRank = minSeverity === "high" ? 3 : minSeverity === "medium" ? 2 : 1;

  // Date cutoff — use internal windows.news_window, falling back to prop
  const effectiveNewsWindow = windows.news_window;
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - effectiveNewsWindow);

  const filtered = newsItems.filter((item) => {
    // Date window filter
    if (item.date) {
      const articleDate = new Date(item.date);
      if (!isNaN(articleDate.getTime()) && articleDate < cutoffDate) return false;
    }
    // Severity threshold filter
    const rank = severityRank[(item.severity ?? "low") as keyof typeof severityRank] ?? 1;
    if (rank < minSeverityRank) return false;
    // Sentiment/material filter
    if (sentimentFilter === "material") return item.is_material;
    if (sentimentFilter === "negative") return item.sentiment === "negative";
    return true;
  });

  const negativeCount = newsItems.filter((n) => n.sentiment === "negative").length;
  const materialCount = newsItems.filter((n) => n.is_material).length;
  const positiveCount = newsItems.filter((n) => n.sentiment === "positive").length;

  return (
    <div className="space-y-6">

      {/* Risk Profile Header */}
      {analysis && (
        <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <h3 className="text-xl font-bold text-[#D71E28] border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
                News & Sentiment Analysis
              </h3>
              <RiskLevel level={analysis.risk_level} />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="text-center p-4 bg-gray-50 rounded border">
              <p className="text-3xl font-bold text-[#333333]">{newsItems.length}</p>
              <p className="text-xs text-[#666666] uppercase tracking-wide mt-1">Total Articles</p>
            </div>
            <div className="text-center p-4 bg-red-50 rounded border border-red-200">
              <p className="text-3xl font-bold text-red-600">{negativeCount}</p>
              <p className="text-xs text-[#666666] uppercase tracking-wide mt-1">Negative</p>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded border border-orange-200">
              <p className="text-3xl font-bold text-orange-600">{materialCount}</p>
              <p className="text-xs text-[#666666] uppercase tracking-wide mt-1">Material Events</p>
            </div>
          </div>

          {analysis.summary && (
            <p className="text-sm text-[#333333] bg-gray-50 rounded p-4 border-l-4 border-[#D71E28]">
              {analysis.summary}
            </p>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            {analysis.key_concerns && analysis.key_concerns.length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-red-700 mb-2">Key Concerns</p>
                <ul className="space-y-1">
                  {analysis.key_concerns.map((c, i) => (
                    <li key={i} className="text-sm text-[#333333] flex items-start gap-2">
                      <span className="text-red-500 mt-0.5">▸</span> {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.positive_signals && analysis.positive_signals.length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-green-700 mb-2">Positive Signals</p>
                <ul className="space-y-1">
                  {analysis.positive_signals.map((s, i) => (
                    <li key={i} className="text-sm text-[#333333] flex items-start gap-2">
                      <span className="text-green-500 mt-0.5">▸</span> {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {analysis.material_events && analysis.material_events.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-bold uppercase tracking-wide text-[#666666] mb-2">Material Event Types</p>
              <div className="flex flex-wrap gap-2">
                {analysis.material_events.map((e, i) => (
                  <span key={i} className="px-2 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded border border-red-300 uppercase tracking-wide">
                    {e.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* News Feed */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <div className="flex flex-col gap-3 mb-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-[#D71E28] border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
              News Feed
            </h3>
            <div className="flex items-center gap-3">
              <span className="text-xs text-[#666666] font-semibold">
                {filtered.length} of {newsItems.length} articles
              </span>
              {/* Settings gear */}
              <div className="relative">
                <button
                  onClick={() => setSettingsOpen(o => !o)}
                  title="Data freshness settings"
                  className={`p-2 rounded-lg border-2 transition-colors text-sm font-bold ${
                    settingsOpen
                      ? "bg-[#D71E28] text-white border-[#D71E28]"
                      : "bg-white text-[#666666] border-gray-300 hover:border-[#D71E28] hover:text-[#D71E28]"
                  }`}
                >
                  Settings
                </button>

                {settingsOpen && (
                  <div className="absolute right-0 top-10 z-20 bg-white border-2 border-gray-200 rounded-lg shadow-xl p-5 w-80">
                    <p className="text-xs font-bold uppercase tracking-widest text-[#333333] mb-4 border-b pb-2">Data Freshness Windows</p>
                    <div className="space-y-5">
                      {([
                        { label: "News window", key: "news_window" as const, min: 7,  max: 365,  step: 7,  unit: "d" },
                        { label: "Financial window", key: "fin_window" as const,  min: 30, max: 730,  step: 30, unit: "d" },
                        { label: "Products window", key: "prod_window" as const, min: 90, max: 1095, step: 30, unit: "d" },
                      ]).map(({ label, key, min, max, step, unit }) => (
                        <div key={key}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-xs font-semibold text-[#555555]">{label}</span>
                            <span className="text-xs font-black text-[#D71E28]">
                              {windows[key] >= 365
                                ? `${(windows[key] / 365).toFixed(windows[key] % 365 === 0 ? 0 : 1)}y`
                                : `${windows[key]}${unit}`}
                            </span>
                          </div>
                          <input
                            type="range"
                            min={min} max={max} step={step}
                            value={windows[key]}
                            onChange={e => handleWindowChange(key, Number(e.target.value))}
                            className="w-full accent-[#D71E28]"
                          />
                          <div className="flex justify-between text-[10px] text-gray-400">
                            <span>{min}{unit}</span><span>{max >= 365 ? `${max/365}y` : `${max}${unit}`}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                    <button
                      onClick={() => setSettingsOpen(false)}
                      className="mt-4 w-full py-1.5 bg-[#D71E28] text-white text-xs font-bold rounded uppercase tracking-wide hover:bg-[#b01820]"
                    >
                      Done
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Threshold controls row */}
          <div className="flex flex-wrap items-center gap-4 bg-gray-50 border border-gray-200 rounded px-4 py-3">
            {/* Time window indicator */}
              <div className="flex items-center gap-2 text-xs text-[#666666]">
                <span className="font-bold uppercase tracking-wide">Time window:</span>
                <span className="font-black text-[#D71E28]">
                  {effectiveNewsWindow >= 365
                    ? `${(effectiveNewsWindow / 365).toFixed(effectiveNewsWindow % 365 === 0 ? 0 : 1)}y`
                    : `${effectiveNewsWindow}d`}
                </span>
              </div>

            <div className="h-4 border-l border-gray-300" />

            {/* Min severity threshold */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wide text-[#666666]">Min severity:</span>
              <div className="flex gap-1">
                {(["all", "medium", "high"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => setMinSeverity(s)}
                    className={`px-2.5 py-1 text-xs font-bold rounded uppercase tracking-wide border transition-colors ${
                      minSeverity === s
                        ? s === "high" ? "bg-red-600 text-white border-red-600"
                          : s === "medium" ? "bg-yellow-500 text-white border-yellow-500"
                          : "bg-[#D71E28] text-white border-[#D71E28]"
                        : "bg-white text-[#666666] border-gray-300 hover:border-gray-400"
                    }`}
                  >
                    {s === "all" ? "All" : s === "medium" ? "Medium+" : "High only"}
                  </button>
                ))}
              </div>
            </div>

            <div className="h-4 border-l border-gray-300" />

            {/* Sentiment/material filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wide text-[#666666]">Show:</span>
              <div className="flex gap-1">
                {(["all", "material", "negative"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setSentimentFilter(f)}
                    className={`px-2.5 py-1 text-xs font-bold rounded uppercase tracking-wide border transition-colors ${
                      sentimentFilter === f
                        ? "bg-[#D71E28] text-white border-[#D71E28]"
                        : "bg-white text-[#666666] border-gray-300 hover:border-gray-400"
                    }`}
                  >
                    {f === "all" ? `All` : f === "material" ? `Material (${materialCount})` : `Negative (${negativeCount})`}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="text-center py-12 text-[#666666]">
            <p className="text-lg font-semibold">No articles match current thresholds</p>
            <button
              onClick={() => { setSentimentFilter("all"); setMinSeverity("all"); }}
              className="mt-2 text-sm text-[#D71E28] underline"
            >
              Reset filters
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((item, idx) => (
              <div
                key={idx}
                className={`p-4 rounded border-l-4 bg-gray-50 ${
                  item.severity === "high"
                    ? "border-red-500"
                    : item.severity === "medium"
                    ? "border-yellow-400"
                    : "border-gray-300"
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* Sparkline — shown when stock data is available for this date */}
                  {item.date && stockData[item.date] && (
                    <div className="flex-shrink-0 flex flex-col items-center pt-1">
                      <StockSparkline data={stockData[item.date]} width={88} height={38} />
                      <span className="text-xs text-gray-400 mt-0.5 whitespace-nowrap">±1 day</span>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h4 className="text-sm font-bold text-[#333333] flex-1">{item.title}</h4>
                      <div className="flex gap-2 flex-shrink-0">
                        <SentimentBadge sentiment={item.sentiment} />
                        <SeverityBadge severity={item.severity} />
                      </div>
                    </div>

                    {item.summary && (
                      <p className="text-xs text-[#555555] mb-2">{item.summary}</p>
                    )}

                    {item.key_facts && item.key_facts.length > 0 && (
                      <ul className="mb-2 space-y-0.5">
                        {item.key_facts.map((f, fi) => (
                          <li key={fi} className="text-xs text-[#666666] flex items-start gap-1">
                            <span className="text-[#D71E28] font-bold">•</span> {f}
                          </li>
                        ))}
                      </ul>
                    )}

                    <div className="flex items-center justify-between mt-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-[#999999]">{item.date || "N/A"}</span>
                        {item.is_material && (
                          <span className="text-xs font-bold text-orange-600 bg-orange-50 border border-orange-200 px-2 py-0.5 rounded uppercase tracking-wide">
                            Material
                          </span>
                        )}
                        {item.event_types && item.event_types.length > 0 && (
                          <div className="flex gap-1">
                            {item.event_types.slice(0, 2).map((e, ei) => (
                              <span key={ei} className="text-xs text-[#666666] bg-gray-200 px-1.5 py-0.5 rounded uppercase tracking-wide">
                                {e.replace(/_/g, " ")}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      {item.url && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-[#D71E28] hover:underline font-semibold"
                        >
                          Read More
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
