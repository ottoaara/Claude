"use client";

import { useEffect, useState } from "react";
import { api, PeerCompanyMetrics } from "@/lib/api";

interface Props {
  companyName: string;
}

interface ComparisonData {
  target: PeerCompanyMetrics;
  peers: PeerCompanyMetrics[];
}

// ─── Colour palette ─────────────────────────────────────────────────────────
const TARGET_COLOR = "#D71E28";   // Wells Fargo red for target
const PEER_COLORS = ["#1d4ed8", "#15803d", "#9333ea", "#c2410c", "#0e7490"];
const AXIS_COLOR = "#e5e7eb";
const LABEL_COLOR = "#6b7280";

// ─── Helpers ─────────────────────────────────────────────────────────────────
function fmtM(v: number | null | undefined): string {
  if (v == null) return "N/A";
  const abs = Math.abs(v);
  if (abs >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}T`;
  if (abs >= 1_000) return `$${(v / 1_000).toFixed(1)}B`;
  return `$${v.toFixed(0)}M`;
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "N/A";
  return `${v.toFixed(1)}%`;
}

// ─── Single horizontal grouped bar chart ────────────────────────────────────
interface BarChartProps {
  title: string;
  subtitle?: string;
  formatter: (v: number | null | undefined) => string;
  entries: { label: string; value: number | null | undefined; color: string }[];
}

function BarChart({ title, subtitle, formatter, entries }: BarChartProps) {
  const valid = entries.filter((e) => e.value != null && isFinite(e.value as number));
  if (valid.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <p className="text-xs font-bold uppercase tracking-wide text-[#666666]">{title}</p>
        <p className="text-sm text-gray-400 mt-2">No data available</p>
      </div>
    );
  }

  const max = Math.max(...valid.map((e) => Math.abs(e.value as number)));
  const ROW_H = 28;
  const LABEL_W = 140;
  const BAR_AREA = 260;
  const VALUE_W = 90;
  const svgW = LABEL_W + BAR_AREA + VALUE_W;
  const svgH = entries.length * ROW_H + 8;

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-xs font-bold uppercase tracking-wide text-[#333333] mb-1">{title}</p>
      {subtitle && <p className="text-xs text-[#666666] mb-2">{subtitle}</p>}
      <svg width="100%" viewBox={`0 0 ${svgW} ${svgH}`} className="overflow-visible">
        {entries.map((e, i) => {
          const y = i * ROW_H + 4;
          const barLen = max > 0 && e.value != null ? (Math.abs(e.value) / max) * BAR_AREA * 0.85 : 0;
          const isNeg = (e.value ?? 0) < 0;
          return (
            <g key={e.label}>
              {/* label */}
              <text
                x={LABEL_W - 6}
                y={y + ROW_H / 2 + 4}
                textAnchor="end"
                fontSize={11}
                fill="#374151"
                fontWeight={e.label === entries[0].label ? "700" : "400"}
              >
                {e.label.length > 18 ? e.label.slice(0, 17) + "…" : e.label}
              </text>
              {/* bar */}
              <rect
                x={LABEL_W}
                y={y + 4}
                width={barLen}
                height={ROW_H - 10}
                rx={3}
                fill={e.value == null ? "#d1d5db" : e.color}
                opacity={isNeg ? 0.65 : 1}
              />
              {/* value */}
              <text
                x={LABEL_W + barLen + 6}
                y={y + ROW_H / 2 + 4}
                fontSize={11}
                fill={e.value == null ? "#9ca3af" : "#111827"}
              >
                {formatter(e.value)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ─── Relationship badge ───────────────────────────────────────────────────────
function RelBadge({ rel }: { rel?: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    direct_competitor: { label: "Direct Competitor", cls: "bg-red-100 text-red-800" },
    industry_peer:     { label: "Industry Peer",     cls: "bg-blue-100 text-blue-800" },
    market_adjacent:   { label: "Market Adjacent",   cls: "bg-purple-100 text-purple-800" },
  };
  const { label, cls } = map[rel ?? ""] ?? { label: "Peer", cls: "bg-gray-100 text-gray-700" };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>{label}</span>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function PeerComparison({ companyName }: Props) {
  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!companyName) return;
    setLoading(true);
    setError(null);
    api.getPeerComparison(companyName)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [companyName]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg border-2 border-gray-200 p-6 text-center">
        <div className="animate-pulse text-[#D71E28] font-semibold">Loading peer comparison…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg border-2 border-gray-200 p-6 text-center">
        <p className="text-[#666666] font-semibold">Peer comparison unavailable</p>
        <p className="text-xs text-gray-400 mt-1">{error}</p>
        <p className="text-xs text-gray-400 mt-1">
          Run research first — EDGAR filings for peers are fetched automatically.
        </p>
      </div>
    );
  }

  if (!data || (!data.peers.length && !data.target.revenue)) {
    return (
      <div className="bg-white rounded-lg border-2 border-gray-200 p-6 text-center">
        <p className="text-[#666666] font-semibold">No peer financial data yet</p>
        <p className="text-xs text-gray-400 mt-1">
          Peer EDGAR data is fetched automatically when you run research for this company.
        </p>
      </div>
    );
  }

  const target = data.target;
  const peers = data.peers.slice(0, 5); // max 5 peers for readability

  // Build ordered entries: target first, then peers
  const allEntries = [
    { ...target, isTarget: true },
    ...peers.map((p) => ({ ...p, isTarget: false })),
  ];

  const colorFor = (i: number, isTarget: boolean) =>
    isTarget ? TARGET_COLOR : PEER_COLORS[(i - 1) % PEER_COLORS.length];

  const toChartEntries = (field: keyof PeerCompanyMetrics) =>
    allEntries.map((e, i) => ({
      label: e.name,
      value: e[field] as number | null | undefined,
      color: colorFor(i, (e as any).isTarget),
    }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-5 border-2 border-gray-200 shadow-md">
        <h3 className="text-2xl font-bold text-[#D71E28] mb-3 border-b-4 border-[#D71E28] pb-3 uppercase tracking-wide">
          Peer Financial Comparison
        </h3>
        <p className="text-sm text-[#666666] mb-4">
          EDGAR 10-K / 10-Q data sourced directly from SEC filings. All values in USD millions.
        </p>

        {/* Legend */}
        <div className="flex flex-wrap gap-3">
          {allEntries.map((e, i) => (
            <div key={e.name} className="flex items-center gap-1.5">
              <div
                className="w-3 h-3 rounded-sm flex-shrink-0"
                style={{ background: colorFor(i, (e as any).isTarget) }}
              />
              <span className="text-xs font-semibold text-[#333333]">
                {e.name}
                {(e as any).isTarget && (
                  <span className="ml-1 text-[10px] text-[#D71E28] font-bold">(TARGET)</span>
                )}
              </span>
              {!(e as any).isTarget && (
                <RelBadge rel={(e as any).relationship} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Charts — 2-column grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <BarChart
          title="Revenue"
          subtitle="Total revenue from most recent filing"
          formatter={fmtM}
          entries={toChartEntries("revenue")}
        />
        <BarChart
          title="Net Income"
          subtitle="Bottom-line profit / loss"
          formatter={fmtM}
          entries={toChartEntries("net_income")}
        />
        <BarChart
          title="Total Assets"
          subtitle="Balance sheet total assets"
          formatter={fmtM}
          entries={toChartEntries("total_assets")}
        />
        <BarChart
          title="Net Margin"
          subtitle="Net income ÷ Revenue"
          formatter={fmtPct}
          entries={toChartEntries("net_margin")}
        />
        <BarChart
          title="Operating Income"
          subtitle="EBIT from most recent filing"
          formatter={fmtM}
          entries={toChartEntries("operating_income")}
        />
        <BarChart
          title="Stockholders' Equity"
          subtitle="Book value of equity"
          formatter={fmtM}
          entries={toChartEntries("stockholders_equity")}
        />
      </div>

      {/* Raw data table */}
      <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-gray-200">
              <th className="text-left p-3 font-bold text-[#333333]">Company</th>
              <th className="text-right p-3 font-bold text-[#333333]">Revenue</th>
              <th className="text-right p-3 font-bold text-[#333333]">Net Income</th>
              <th className="text-right p-3 font-bold text-[#333333]">Net Margin</th>
              <th className="text-right p-3 font-bold text-[#333333]">Total Assets</th>
              <th className="text-right p-3 font-bold text-[#333333]">Period</th>
            </tr>
          </thead>
          <tbody>
            {allEntries.map((e, i) => (
              <tr
                key={e.name}
                className={`border-b border-gray-100 ${(e as any).isTarget ? "bg-red-50" : "hover:bg-gray-50"}`}
              >
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                      style={{ background: colorFor(i, (e as any).isTarget) }}
                    />
                    <span className={`font-semibold ${(e as any).isTarget ? "text-[#D71E28]" : "text-[#333333]"}`}>
                      {e.name}
                    </span>
                    {e.ticker && (
                      <span className="text-xs text-gray-400">({e.ticker})</span>
                    )}
                  </div>
                </td>
                <td className="p-3 text-right font-mono text-[#333333]">{fmtM(e.revenue)}</td>
                <td className="p-3 text-right font-mono">
                  <span className={e.net_income != null && e.net_income < 0 ? "text-red-600" : "text-[#333333]"}>
                    {fmtM(e.net_income)}
                  </span>
                </td>
                <td className="p-3 text-right font-mono">
                  <span className={e.net_margin != null && e.net_margin < 0 ? "text-red-600" : "text-green-700"}>
                    {fmtPct(e.net_margin)}
                  </span>
                </td>
                <td className="p-3 text-right font-mono text-[#333333]">{fmtM(e.total_assets)}</td>
                <td className="p-3 text-right text-gray-500 text-xs">
                  {e.filing_type} {e.filing_period}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
