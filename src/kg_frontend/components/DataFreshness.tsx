"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { api, APIError } from "../lib/api";

interface FreshnessItem {
  label: string;
  age_days: number | null;
  score: number;
  freshness: "fresh" | "recent" | "aged" | "stale";
  source?: string;
  sentiment?: string;
}

interface DimensionFreshness {
  items: FreshnessItem[];
  avg_score: number;
  window_days: number;
  needs_refresh: boolean;
}

interface FreshnessData {
  company_name: string;
  overall_score: number;
  overall_freshness: string;
  dimensions: {
    financials: DimensionFreshness;
    news: DimensionFreshness;
    products: DimensionFreshness;
  };
  temporal_summary?: {
    total_items: number;
    fresh_items: number;
    recent_items: number;
    aged_items: number;
    stale_items: number;
    avg_relevance_score: number;
    oldest_item_age_days: number;
    newest_item_age_days: number;
  };
  freshness_updated_at?: string;
}

interface WindowConfig {
  fin_window: number;
  news_window: number;
  prod_window: number;
}

interface Props {
  companyName: string;
  onWindowChange?: (w: WindowConfig) => void;
}

const FRESHNESS_CONFIG = {
  fresh:  { color: "text-green-700",  bg: "bg-green-50",  border: "border-green-300",  bar: "bg-green-500",  label: "Fresh" },
  recent: { color: "text-blue-700",   bg: "bg-blue-50",   border: "border-blue-300",   bar: "bg-blue-500",   label: "Recent" },
  aged:   { color: "text-yellow-700", bg: "bg-yellow-50", border: "border-yellow-300", bar: "bg-yellow-500", label: "Aged" },
  stale:  { color: "text-red-700",    bg: "bg-red-50",    border: "border-red-300",    bar: "bg-red-500",    label: "Stale" },
};

const DIMENSION_META: Record<string, { label: string; description: string; windowKey: keyof WindowConfig; min: number; max: number; step: number }> = {
  financials: { label: "Financial Data",    description: "SEC 10-K / 10-Q filings", windowKey: "fin_window",  min: 30,  max: 730, step: 30 },
  news:       { label: "News & Sentiment",  description: "Recent news articles",     windowKey: "news_window", min: 7,   max: 365, step: 7  },
  products:   { label: "Product Portfolio", description: "Banking product data",     windowKey: "prod_window", min: 90,  max: 1095,step: 30 },
};

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const cfg = score >= 0.8 ? FRESHNESS_CONFIG.fresh
            : score >= 0.5 ? FRESHNESS_CONFIG.recent
            : score >= 0.3 ? FRESHNESS_CONFIG.aged
            : FRESHNESS_CONFIG.stale;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded overflow-hidden">
        <div className={`h-full rounded ${cfg.bar} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-bold w-8 text-right ${cfg.color}`}>{pct}%</span>
    </div>
  );
}

function FreshnessBadge({ freshness }: { freshness: string }) {
  const cfg = FRESHNESS_CONFIG[freshness as keyof typeof FRESHNESS_CONFIG] ?? FRESHNESS_CONFIG.stale;
  return (
    <span className={`px-2 py-0.5 text-xs font-bold rounded border uppercase tracking-wide ${cfg.color} ${cfg.bg} ${cfg.border}`}>
      {cfg.label}
    </span>
  );
}

function OverallGauge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const r = 52, cx = 64, cy = 64;
  const circumference = Math.PI * r;
  const offset = circumference * (1 - score);
  const color = score >= 0.8 ? "#16a34a" : score >= 0.5 ? "#2563eb" : score >= 0.3 ? "#d97706" : "#dc2626";
  return (
    <div className="flex flex-col items-center">
      <svg width="128" height="80" viewBox="0 0 128 80">
        <path d={`M 12 64 A ${r} ${r} 0 0 1 116 64`} fill="none" stroke="#e5e7eb" strokeWidth="12" strokeLinecap="round" />
        <path d={`M 12 64 A ${r} ${r} 0 0 1 116 64`} fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={`${circumference}`} strokeDashoffset={`${offset}`}
          style={{ transition: "stroke-dashoffset 0.6s ease" }} />
        <text x="64" y="58" textAnchor="middle" fontSize="22" fontWeight="bold" fill={color}>{pct}%</text>
        <text x="64" y="74" textAnchor="middle" fontSize="10" fill="#6b7280">Data Freshness</text>
      </svg>
    </div>
  );
}

function WindowSlider({
  label, windowKey, value, min, max, step, onChange, refetching,
}: {
  label: string; windowKey: string; value: number; min: number; max: number; step: number;
  onChange: (key: keyof WindowConfig, val: number) => void; refetching: boolean;
}) {
  const displayDays = value >= 365
    ? `${(value / 365).toFixed(value % 365 === 0 ? 0 : 1)}y`
    : `${value}d`;

  return (
    <div className="flex items-center gap-3 bg-gray-50 border border-gray-200 rounded px-3 py-2">
      <span className="text-xs font-bold text-[#666666] uppercase tracking-wide whitespace-nowrap">
        Relevance window
      </span>
      <input
        type="range"
        min={min} max={max} step={step} value={value}
        onChange={e => onChange(windowKey as keyof WindowConfig, Number(e.target.value))}
        className="flex-1 accent-[#D71E28] h-1.5 cursor-pointer"
      />
      <span className="text-sm font-black text-[#D71E28] w-10 text-right tabular-nums">
        {displayDays}
      </span>
      {refetching && (
        <span className="w-3 h-3 border-2 border-[#D71E28] border-t-transparent rounded-full animate-spin flex-shrink-0" />
      )}
    </div>
  );
}

export default function DataFreshness({ companyName, onWindowChange }: Props) {
  const [data, setData]           = useState<FreshnessData | null>(null);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState("");
  const [expanded, setExpanded]   = useState<string | null>(null);
  const [windows, setWindows]     = useState<WindowConfig | null>(null);
  const [refetching, setRefetching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Initial load
  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const result = await api.getFreshness(companyName);
        setData(result);
        // Seed sliders from whatever windows the API returned
        setWindows({
          fin_window:  result.dimensions?.financials?.window_days  ?? 365,
          news_window: result.dimensions?.news?.window_days        ?? 90,
          prod_window: result.dimensions?.products?.window_days    ?? 730,
        });
      } catch (err) {
        setError(err instanceof APIError ? err.message : "Failed to load freshness data");
      } finally {
        setLoading(false);
      }
    })();
  }, [companyName]);

  // Debounced refetch when windows change
  const refetch = useCallback(async (w: WindowConfig) => {
    setRefetching(true);
    try {
      const result = await api.getFreshness(companyName, w);
      setData(result);
    } catch {
      // keep existing data on error
    } finally {
      setRefetching(false);
    }
  }, [companyName]);

  const handleWindowChange = useCallback((key: keyof WindowConfig, val: number) => {
    setWindows(prev => {
      if (!prev) return prev;
      const next = { ...prev, [key]: val };
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        refetch(next);
        onWindowChange?.(next);
      }, 500);
      return next;
    });
  }, [refetch, onWindowChange]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-12 text-center border-2 border-gray-200">
        <div className="inline-block w-12 h-12 border-4 border-[#D71E28] border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-[#666666] font-semibold">Computing data freshness...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border-2 border-red-300 rounded p-8 text-red-700">
        <p className="font-bold mb-1 uppercase tracking-wide text-sm">Error</p>
        <p>{error || "No freshness data available — run a research job first."}</p>
      </div>
    );
  }

  const ts = data.temporal_summary;

  return (
    <div className="space-y-6">

      {/* Overall freshness card */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-[#D71E28] border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
            Data Freshness Score
          </h3>
          {refetching && (
            <span className="text-xs text-[#D71E28] font-bold flex items-center gap-1.5">
              <span className="w-3 h-3 border-2 border-[#D71E28] border-t-transparent rounded-full animate-spin" />
              Recalculating…
            </span>
          )}
        </div>

        <div className="flex flex-col md:flex-row items-center gap-8">
          <OverallGauge score={data.overall_score} />
          <div className="flex-1 space-y-3">
            <div className="flex items-center gap-3">
              <FreshnessBadge freshness={data.overall_freshness} />
              <span className="text-sm text-[#666666]">
                Overall data quality across {(ts?.total_items ?? 0)} items
              </span>
            </div>
            {ts && (
              <div className="grid grid-cols-4 gap-3 mt-2">
                {[
                  { label: "Fresh",  value: ts.fresh_items,  color: "text-green-700 bg-green-50 border-green-200" },
                  { label: "Recent", value: ts.recent_items, color: "text-blue-700 bg-blue-50 border-blue-200" },
                  { label: "Aged",   value: ts.aged_items,   color: "text-yellow-700 bg-yellow-50 border-yellow-200" },
                  { label: "Stale",  value: ts.stale_items,  color: "text-red-700 bg-red-50 border-red-200" },
                ].map((b) => (
                  <div key={b.label} className={`text-center p-3 rounded border ${b.color}`}>
                    <p className="text-2xl font-bold">{b.value}</p>
                    <p className="text-xs uppercase tracking-wide mt-0.5">{b.label}</p>
                  </div>
                ))}
              </div>
            )}
            {ts && (
              <div className="flex gap-6 text-xs text-[#666666] mt-1">
                <span>Newest: <strong>{ts.newest_item_age_days}d ago</strong></span>
                <span>Oldest: <strong>{ts.oldest_item_age_days}d ago</strong></span>
                <span>Avg score: <strong>{Math.round(ts.avg_relevance_score * 100)}%</strong></span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Per-dimension breakdown */}
      {(Object.entries(data.dimensions) as [string, DimensionFreshness][]).map(([key, dim]) => {
        const meta   = DIMENSION_META[key as keyof typeof DIMENSION_META];
        const isOpen = expanded === key;
        const winVal = windows?.[meta.windowKey] ?? dim.window_days;

        return (
          <div key={key} className="bg-white rounded-lg border-2 border-gray-200 shadow-md overflow-hidden">

            {/* Header row — always visible */}
            <button
              className="w-full flex items-center justify-between p-5 text-left hover:bg-gray-50 transition-colors"
              onClick={() => setExpanded(isOpen ? null : key)}
            >
              <div className="flex items-center gap-3">
                <div>
                  <p className="font-bold text-[#333333]">{meta.label}</p>
                  <p className="text-xs text-[#666666]">{meta.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {dim.needs_refresh && (
                  <span className="text-xs font-bold text-orange-600 bg-orange-50 border border-orange-200 px-2 py-1 rounded">
                    Needs Refresh
                  </span>
                )}
                <div className="w-32">
                  <ScoreBar score={dim.avg_score} />
                </div>
                <span className="text-[#666666] text-sm font-bold">{isOpen ? "Close" : "Open"}</span>
              </div>
            </button>

            {/* Window slider — always visible below header */}
            {windows && (
              <div className="px-5 pb-4 -mt-1">
                <WindowSlider
                  label={meta.label}
                  windowKey={meta.windowKey}
                  value={winVal}
                  min={meta.min}
                  max={meta.max}
                  step={meta.step}
                  onChange={handleWindowChange}
                  refetching={refetching}
                />
              </div>
            )}

            {/* Expanded items list */}
            {isOpen && (
              <div className="border-t-2 border-gray-100 p-5">
                {dim.items.length === 0 ? (
                  <p className="text-sm text-[#666666] text-center py-4">No data available for this dimension</p>
                ) : (
                  <div className="space-y-2">
                    {dim.items.map((item, i) => (
                      <div key={i} className="flex items-center gap-3 p-3 rounded bg-gray-50 border border-gray-200">
                        <FreshnessBadge freshness={item.freshness} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-semibold text-[#333333] truncate">{item.label}</p>
                          <p className="text-xs text-[#999999]">
                            {item.age_days !== null ? `${item.age_days} days ago` : "Date unknown"}
                            {item.source ? ` · ${item.source}` : ""}
                          </p>
                        </div>
                        <div className="w-28 flex-shrink-0">
                          <ScoreBar score={item.score} />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

