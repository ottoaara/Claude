"use client";

import { useEffect, useState } from "react";
import { api, APIError } from "../lib/api";

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

export default function NewsAnalysis({ companyName }: Props) {
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [analysis, setAnalysis] = useState<NewsAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<"all" | "material" | "negative">("all");

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const data = await api.getCompanyGraph(companyName);
        setNewsItems(data.news || []);
        setAnalysis(data.news_analysis || null);
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
  }, [companyName]);

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

  const filtered = newsItems.filter((item) => {
    if (filter === "material") return item.is_material;
    if (filter === "negative") return item.sentiment === "negative";
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
            <h3 className="text-xl font-bold text-[#D71E28] border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
              News & Sentiment Analysis
            </h3>
            <RiskLevel level={analysis.risk_level} />
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
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-[#D71E28] border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
            News Feed
          </h3>
          {/* Filter Controls */}
          <div className="flex gap-2">
            {(["all", "material", "negative"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 text-xs font-bold rounded uppercase tracking-wide border transition-colors ${
                  filter === f
                    ? "bg-[#D71E28] text-white border-[#D71E28]"
                    : "bg-white text-[#666666] border-gray-300 hover:border-[#D71E28] hover:text-[#D71E28]"
                }`}
              >
                {f === "all" ? `All (${newsItems.length})` : f === "material" ? `Material (${materialCount})` : `Negative (${negativeCount})`}
              </button>
            ))}
          </div>
        </div>

        {filtered.length === 0 ? (
          <div className="text-center py-12 text-[#666666]">
            <p className="text-lg font-semibold">No articles match this filter</p>
            <button onClick={() => setFilter("all")} className="mt-2 text-sm text-[#D71E28] underline">
              Show all articles
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
                      Read More →
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
