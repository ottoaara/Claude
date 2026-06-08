"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { CovenantTooltip } from "./ScoreTooltip";

interface Ratio {
  value: number | null;
  threshold: number;
  label: string;
  higher_is_worse: boolean;
  status: "green" | "yellow" | "red" | "unknown";
}

interface Period {
  period: string;
  filing_type: string;
  ratios: Record<string, Ratio>;
}

const STATUS_STYLES = {
  green:   { bar: "bg-green-500",  text: "text-green-700",  bg: "bg-green-50",  border: "border-green-300",  label: "Healthy" },
  yellow:  { bar: "bg-amber-500",  text: "text-amber-700",  bg: "bg-amber-50",  border: "border-amber-300",  label: "Watch" },
  red:     { bar: "bg-red-500",    text: "text-red-700",    bg: "bg-red-50",    border: "border-red-400",    label: "Breach Risk" },
  unknown: { bar: "bg-gray-300",   text: "text-gray-500",   bg: "bg-gray-50",   border: "border-gray-200",   label: "N/A" },
};

const OVERALL_STYLES = {
  green:   "bg-green-600",
  yellow:  "bg-amber-500",
  red:     "bg-red-600",
  unknown: "bg-gray-400",
};

function RatioCard({ ratio, name }: { ratio: Ratio; name: string }) {
  const s = STATUS_STYLES[ratio.status] ?? STATUS_STYLES.unknown;
  const pct = ratio.value === null ? 0
    : ratio.higher_is_worse
      ? Math.min(100, Math.round((ratio.value / (ratio.threshold * 1.5)) * 100))
      : Math.min(100, Math.round((ratio.value / (ratio.threshold * 2)) * 100));

  return (
    <div className={`rounded-lg border-2 p-4 ${s.bg} ${s.border}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-bold uppercase tracking-wide text-[#555555]">{ratio.label}</span>
        <CovenantTooltip status={ratio.status} ratioLabel={ratio.label} value={ratio.value} threshold={ratio.threshold}>
          <span className={`text-xs font-bold px-2 py-0.5 rounded uppercase cursor-help ${s.text} ${s.bg} border ${s.border}`}>
            {s.label}
          </span>
        </CovenantTooltip>
      </div>
      <div className="flex items-end gap-2 mb-2">
        <span className={`text-2xl font-black ${s.text}`}>
          {ratio.value === null ? "—" : ratio.value}
          {ratio.label.includes("%") ? "%" : "x"}
        </span>
        <span className="text-xs text-[#888888] mb-1">
          threshold: {ratio.threshold}{ratio.label.includes("%") ? "%" : "x"}
        </span>
      </div>
      <div className="h-2 bg-white/60 rounded overflow-hidden">
        <div className={`h-full rounded ${s.bar} transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function CovenantWatch({ companyName }: { companyName: string }) {
  const [data, setData] = useState<{ overall_status: string; periods: Period[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCovenantWatch(companyName)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [companyName]);

  if (loading) return (
    <div className="bg-white rounded-lg border-2 border-gray-200 p-5 shadow-md animate-pulse">
      <div className="h-5 bg-gray-100 rounded w-48 mb-4" />
      <div className="grid grid-cols-3 gap-3">{[1,2,3].map(i => <div key={i} className="h-24 bg-gray-100 rounded" />)}</div>
    </div>
  );

  if (!data || data.periods.length === 0) return (
    <div className="bg-white rounded-lg border-2 border-gray-200 p-5 shadow-md">
      <h4 className="text-base font-bold text-[#333333] uppercase tracking-wide mb-2">Covenant Watch</h4>
      <p className="text-sm text-[#888888]">No financial data available for ratio analysis.</p>
    </div>
  );

  const latest = data.periods[0];
  const overallStyle = OVERALL_STYLES[data.overall_status as keyof typeof OVERALL_STYLES] ?? OVERALL_STYLES.unknown;

  return (
    <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md p-5">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-bold text-[#333333] border-b-4 border-[#333333] pb-2 inline-block uppercase tracking-wide">
          Covenant Watch
        </h4>
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${overallStyle}`} />
          <span className="text-xs font-bold text-[#555555] uppercase tracking-wide">
            {latest.period} · {data.overall_status === "green" ? "All Clear" : data.overall_status === "yellow" ? "Monitor" : "Breach Risk"}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {Object.entries(latest.ratios).map(([key, ratio]) => (
          <RatioCard key={key} name={key} ratio={ratio} />
        ))}
      </div>
      {data.periods.length > 1 && (
        <p className="text-xs text-[#888888] mt-3">
          Showing latest period. {data.periods.length} periods available.
        </p>
      )}
    </div>
  );
}
