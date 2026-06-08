"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "../../lib/api";
import { GradeTooltip, NewsRiskTooltip, ComponentTooltip } from "../../components/ScoreTooltip";

const RISK_COLORS = {
  high:    "bg-red-100 text-red-800 border-red-300",
  medium:  "bg-amber-100 text-amber-800 border-amber-300",
  low:     "bg-green-100 text-green-800 border-green-300",
  unknown: "bg-gray-100 text-gray-600 border-gray-200",
};

const HEAT_COLORS = [
  "bg-green-100 border-green-300 text-green-900",
  "bg-amber-100 border-amber-300 text-amber-900",
  "bg-orange-100 border-orange-300 text-orange-900",
  "bg-red-100 border-red-400 text-red-900",
];

function heat(score: number) {
  if (score < 3) return HEAT_COLORS[0];
  if (score < 5) return HEAT_COLORS[1];
  if (score < 7) return HEAT_COLORS[2];
  return HEAT_COLORS[3];
}

export default function PortfolioDashboard() {
  const [portfolio, setPortfolio] = useState<any[]>([]);
  const [heatmap, setHeatmap] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState<string>("pitch_score");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getPortfolio().catch(() => ({ companies: [] })),
      api.getIndustryHeatmap().catch(() => ({ sectors: [] })),
    ]).then(([p, h]) => {
      setPortfolio(p.companies || []);
      setHeatmap(h.sectors || []);
    }).finally(() => setLoading(false));
  }, []);

  const sortBy = (field: string) => {
    if (sort === field) setSortDir(d => (d === 1 ? -1 : 1));
    else { setSort(field); setSortDir(1); }
  };

  const sorted = [...portfolio].sort((a, b) => {
    const av = a[sort] ?? "";
    const bv = b[sort] ?? "";
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * sortDir;
    return String(av).localeCompare(String(bv)) * sortDir;
  });

  const totalCompanies = portfolio.length;
  const activeDeals = portfolio.reduce((s, c) => s + (c.active_deals || 0), 0);
  const neverContacted = portfolio.filter(c => !c.last_contact).length;
  const highNews = portfolio.filter(c => c.news_risk === "high").length;
  const topOpportunities = portfolio.filter(c => (c.pitch_score ?? 0) >= 60).length;

  const SortBtn = ({ field, label }: { field: string; label: string }) => (
    <button onClick={() => sortBy(field)}
      className="text-left font-bold text-xs uppercase tracking-wide text-white hover:text-[#FFCD41] whitespace-nowrap">
      {label} {sort === field ? (sortDir === 1 ? "(asc)" : "(desc)") : ""}
    </button>
  );

  if (loading) return (
    <div className="min-h-screen bg-[#F5F5F0] p-8 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-[#D71E28] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-[#666666] font-semibold">Loading portfolio…</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#F5F5F0]">
      {/* Header */}
      <div className="bg-[#D71E28] shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <Link href="/banking" className="text-white/70 hover:text-white text-sm">← Research</Link>
              </div>
              <h1 className="text-2xl font-black text-white uppercase tracking-wide">RM Portfolio Dashboard</h1>
              <p className="text-white/70 text-sm">{totalCompanies} companies in coverage</p>
            </div>
            <div className="flex gap-6 text-center">
              <div>
                <p className="text-3xl font-black text-white">{totalCompanies}</p>
                <p className="text-white/70 text-xs uppercase tracking-wide">Companies</p>
              </div>
              <div>
                <p className="text-3xl font-black text-white">{activeDeals}</p>
                <p className="text-white/70 text-xs uppercase tracking-wide">Active Deals</p>
              </div>
              <div>
                <p className={`text-3xl font-black ${highNews > 0 ? "text-[#FFCD41]" : "text-white"}`}>{highNews}</p>
                <p className="text-white/70 text-xs uppercase tracking-wide">High Risk</p>
              </div>
              <div>
                <p className={`text-3xl font-black ${neverContacted > 0 ? "text-[#FFCD41]" : "text-white"}`}>{neverContacted}</p>
                <p className="text-white/70 text-xs uppercase tracking-wide">No Contact</p>
              </div>
              <div>
                <p className={`text-3xl font-black ${topOpportunities > 0 ? "text-[#FFCD41]" : "text-white"}`}>{topOpportunities}</p>
                <p className="text-white/70 text-xs uppercase tracking-wide">Top Opps (B+)</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 space-y-8">
        {/* Portfolio table */}
        <div className="bg-white rounded-xl border-2 border-gray-200 shadow-md overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-[#333333]">
                  <th className="px-4 py-3 text-left"><SortBtn field="name" label="Company" /></th>
                  <th className="px-4 py-3 text-left"><SortBtn field="ticker" label="Ticker" /></th>
                  <th className="px-4 py-3 text-left"><SortBtn field="industry" label="Industry" /></th>
                  <th className="px-4 py-3 text-center"><SortBtn field="news_risk" label="News Risk" /></th>
                  <th className="px-4 py-3 text-center"><SortBtn field="last_contact" label="Last Contact" /></th>
                  <th className="px-4 py-3 text-center"><SortBtn field="activity_count" label="Contacts" /></th>
                  <th className="px-4 py-3 text-center"><SortBtn field="deal_count" label="Deals" /></th>
                  <th className="px-4 py-3 text-center"><SortBtn field="active_deals" label="Active" /></th>
                  <th className="px-4 py-3 text-center"><SortBtn field="news_count" label="News" /></th>
                  <th className="px-4 py-3 text-center"><SortBtn field="pitch_score" label="Opp Score" /></th>
                  <th className="px-4 py-3 text-center text-white text-xs font-bold uppercase tracking-wide">Open</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((c, i) => {
                  const daysAgo = c.last_contact
                    ? Math.floor((Date.now() - new Date(c.last_contact).getTime()) / 86400000)
                    : null;
                  return (
                    <React.Fragment key={c.name}>
                    <tr className={`border-b border-gray-100 hover:bg-gray-50 ${expandedRow === c.name ? "bg-blue-50/40" : i % 2 === 0 ? "" : "bg-gray-50/50"}`}>
                      <td className="px-4 py-3 font-semibold text-[#333333]">{c.name}</td>
                      <td className="px-4 py-3 text-[#666666] font-mono text-xs">{c.ticker || "—"}</td>
                      <td className="px-4 py-3 text-[#666666] text-xs max-w-32 truncate">{c.industry || "—"}</td>
                      <td className="px-4 py-3 text-center">
                        <NewsRiskTooltip risk={c.news_risk || "unknown"}>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase cursor-help ${RISK_COLORS[c.news_risk as keyof typeof RISK_COLORS] ?? RISK_COLORS.unknown}`}>
                            {c.news_risk || "n/a"}
                          </span>
                        </NewsRiskTooltip>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {daysAgo !== null ? (
                          <span className={`text-xs font-semibold ${daysAgo > 60 ? "text-red-600" : daysAgo > 30 ? "text-amber-600" : "text-green-700"}`}>
                            {daysAgo}d ago
                          </span>
                        ) : <span className="text-xs text-gray-400">none</span>}
                      </td>
                      <td className="px-4 py-3 text-center text-[#333333] font-semibold">{c.activity_count ?? 0}</td>
                      <td className="px-4 py-3 text-center text-[#333333] font-semibold">{c.deal_count ?? 0}</td>
                      <td className="px-4 py-3 text-center">
                        {(c.active_deals ?? 0) > 0
                          ? <span className="text-xs font-bold text-green-700 bg-green-50 px-2 py-0.5 rounded">{c.active_deals}</span>
                          : <span className="text-xs text-gray-400">0</span>}
                      </td>
                      <td className="px-4 py-3 text-center text-[#666666]">{c.news_count ?? 0}</td>
                      <td className="px-4 py-3 text-center">
                        {c.pitch_score != null ? (
                          <GradeTooltip grade={c.pitch_grade} score={c.pitch_score} breakdown={c.pitch_breakdown}>
                            <button
                              onClick={() => setExpandedRow(expandedRow === c.name ? null : c.name)}
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-black text-xs border cursor-pointer hover:opacity-80 transition-opacity ${
                                c.pitch_grade === "A" ? "bg-green-100 text-green-800 border-green-400" :
                                c.pitch_grade === "B" ? "bg-blue-100 text-blue-800 border-blue-400" :
                                c.pitch_grade === "C" ? "bg-amber-100 text-amber-800 border-amber-400" :
                                c.pitch_grade === "D" ? "bg-orange-100 text-orange-800 border-orange-400" :
                                "bg-gray-100 text-gray-600 border-gray-300"
                              }`}
                              title="Hover for grade rules · Click to see breakdown"
                            >
                              {c.pitch_score}<span className="opacity-60 font-normal">/100</span>
                              <span className="ml-0.5">{c.pitch_grade}</span>
                              <span className="opacity-40 text-[9px] ml-0.5">{expandedRow === c.name ? "▲" : "▼"}</span>
                            </button>
                          </GradeTooltip>
                        ) : <span className="text-xs text-gray-400">—</span>}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <Link
                          href={`/banking?company=${encodeURIComponent(c.name)}`}
                          className="text-xs font-bold text-[#D71E28] hover:underline uppercase tracking-wide"
                        >
                          Research
                        </Link>
                      </td>
                    </tr>
                    {expandedRow === c.name && c.pitch_breakdown && (
                      <tr className="bg-blue-50/60 border-b border-blue-100">
                        <td colSpan={11} className="px-6 py-4">
                          <div className="max-w-2xl">
                            <p className="text-[10px] font-bold uppercase tracking-widest text-[#666] mb-3">Score Breakdown — what is driving this opportunity</p>
                            <div className="space-y-2">
                              {([
                                { key: "timing",            label: "Timing",            desc: "Long-term debt + filing recency" },
                                { key: "covenant_stress",    label: "Covenant Stress",    desc: "Interest coverage, net margin, ROA vs thresholds" },
                                { key: "deal_triggers",      label: "Deal Triggers",      desc: "News risk level + material events + contact gap boost" },
                                { key: "relationship_warmth",label: "Relationship Warmth",desc: "Fresh board/alumni connections with WF officers" },
                                { key: "contact_gap",        label: "Contact Gap",        desc: c.pitch_breakdown.contact_gap?.days_since_contact != null
                                  ? `Last contact ${c.pitch_breakdown.contact_gap.days_since_contact} days ago`
                                  : "No contact on record" },
                              ] as { key: string; label: string; desc: string }[]).map(({ key, label, desc }) => {
                                const comp = c.pitch_breakdown[key];
                                if (!comp) return null;
                                const pct = Math.round((comp.score / comp.max) * 100);
                                return (
                                  <div key={key} className="flex items-center gap-3">
                                    <div className="w-36 shrink-0">
                                      <p className="text-xs font-bold text-[#333]">{label}</p>
                                      <p className="text-[10px] text-[#888] leading-tight">{desc}</p>
                                    </div>
                                    <ComponentTooltip componentKey={key} pct={pct} pts={comp.score}>
                                      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                                        <div
                                          className={`h-full rounded-full transition-all ${
                                            pct >= 70 ? "bg-[#D71E28]" : pct >= 40 ? "bg-amber-500" : "bg-gray-400"
                                          }`}
                                          style={{ width: `${pct}%` }}
                                        />
                                      </div>
                                    </ComponentTooltip>
                                    <div className="w-16 text-right shrink-0">
                                      <span className="text-xs font-black text-[#333]">{comp.score}</span>
                                      <span className="text-[10px] text-[#999]">/{comp.max}</span>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                    </React.Fragment>
                  );
                })}
                {sorted.length === 0 && (
                  <tr><td colSpan={11} className="px-4 py-8 text-center text-[#888888]">No companies in portfolio. Run research on companies to populate.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Industry Heatmap */}
        {heatmap.length > 0 && (
          <div>
            <h2 className="text-xl font-black text-[#333333] uppercase tracking-wide mb-4 border-b-4 border-[#D71E28] pb-2 inline-block">
              Industry Heat Map
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {heatmap.map((s: any, i: number) => (
                <div key={i} className={`rounded-xl border-2 p-5 shadow-sm ${heat(s.risk_score)}`}>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wide opacity-60 mb-1">{s.naics_code || "SECTOR"}</p>
                      <p className="font-black text-base leading-tight">{s.sector_name}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-black">{s.risk_score?.toFixed(1) ?? "—"}</p>
                      <p className="text-[10px] font-bold uppercase tracking-wide opacity-60">risk score</p>
                    </div>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span><b>{s.company_count ?? 0}</b> companies</span>
                    <span><b>{s.avg_news_sentiment ?? "—"}</b> sentiment</span>
                    <span><b>{s.deal_count ?? 0}</b> deals</span>
                  </div>
                  {s.top_risk && (
                    <p className="text-xs mt-2 opacity-70 italic">Top risk: {s.top_risk}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
