"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";

const URGENCY_COLORS: Record<string, string> = {
  high:   "bg-red-50 border-red-400 text-red-800",
  medium: "bg-amber-50 border-amber-400 text-amber-800",
  low:    "bg-gray-50 border-gray-300 text-gray-600",
};

const CATEGORY_COLORS: Record<string, string> = {
  "Treasury Management": "bg-blue-100 text-blue-800",
  "Credit & Lending":    "bg-green-100 text-green-800",
  "Capital Markets":     "bg-purple-100 text-purple-800",
  "Trade Finance":       "bg-amber-100 text-amber-800",
  "Risk Management":     "bg-orange-100 text-orange-800",
  "Deposits":            "bg-teal-100 text-teal-800",
};

export default function IncumbentBank({ companyName }: { companyName: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showAdvantages, setShowAdvantages] = useState(true);

  const fetch = () => {
    setLoading(true);
    api.getIncumbentBank(companyName)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  };

  if (!data && !loading) return (
    <div className="bg-white rounded-lg border-2 border-gray-200 p-5 shadow-md">
      <h4 className="text-base font-bold text-[#333333] uppercase tracking-wide mb-2">Incumbent Bank</h4>
      <p className="text-xs text-[#888888] mb-3">
        Search SEC filings and public sources to identify the company's current banking relationships and surface WF displacement opportunities.
      </p>
      <button
        onClick={fetch}
        className="px-4 py-2 bg-[#D71E28] hover:bg-[#b01820] text-white text-xs font-bold rounded uppercase tracking-wide transition-colors"
      >
        Detect Incumbent Bank
      </button>
    </div>
  );

  if (loading) return (
    <div className="bg-white rounded-lg border-2 border-gray-200 p-5 shadow-md">
      <div className="flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-[#D71E28] border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-[#666666]">Searching SEC filings and analysing WF opportunities…</span>
      </div>
    </div>
  );

  const wfInvolved = data?.wells_fargo_involved;
  const confidence = data?.confidence ?? "low";
  const urgency    = data?.urgency_rating ?? "medium";
  const confColors = {
    high:   "text-green-700 bg-green-50 border-green-300",
    medium: "text-amber-700 bg-amber-50 border-amber-300",
    low:    "text-gray-600 bg-gray-50 border-gray-300",
  };
  const maturityColors: Record<string, string> = {
    maturing_this_year: "bg-red-100 text-red-800 border-red-400",
    within_12_months:   "bg-red-50 text-red-700 border-red-300",
    within_24_months:   "bg-amber-50 text-amber-800 border-amber-300",
    past_due:           "bg-gray-100 text-gray-600 border-gray-300",
    current:            "bg-green-50 text-green-700 border-green-300",
  };
  const maturityStatus = data?.maturity_status as string;
  const advantages: any[] = data?.wf_advantages ?? [];

  return (
    <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <h4 className="text-lg font-bold text-[#333333] uppercase tracking-wide">Incumbent Bank</h4>
        <div className="flex gap-2 items-center">
          {data?.urgency_rating && (
            <span className={`text-xs font-bold px-2 py-1 rounded border uppercase tracking-wide ${URGENCY_COLORS[urgency] ?? URGENCY_COLORS.medium}`}>
              {urgency} urgency
            </span>
          )}
          <span className={`text-xs font-bold px-2 py-1 rounded border uppercase tracking-wide ${confColors[confidence as keyof typeof confColors] ?? confColors.low}`}>
            {confidence} confidence
          </span>
          <button onClick={fetch} className="text-xs text-[#D71E28] hover:underline font-bold">Refresh</button>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Primary bank card */}
        <div className={`rounded-lg p-4 ${wfInvolved ? "bg-green-50 border-2 border-green-400" : "bg-gray-50 border-2 border-gray-200"}`}>
          <p className="text-xs font-bold uppercase tracking-wide text-[#666666] mb-1">Administrative Agent / Lead Bank</p>
          <div className="flex items-baseline gap-3 flex-wrap">
            <p className="text-xl font-black text-[#333333]">{data?.primary_bank || "Not identified"}</p>
            {wfInvolved
              ? <span className="text-sm font-bold text-green-700 bg-green-100 px-2 py-0.5 rounded">WF already involved — expand wallet share</span>
              : <span className="text-sm font-bold text-[#D71E28] bg-red-50 px-2 py-0.5 rounded">WF not involved — displacement opportunity</span>
            }
          </div>
          {data?.facility_type && (
            <p className="text-xs text-[#666666] mt-2">
              {data.facility_type}
              {data.facility_size && ` · ${data.facility_size}`}
              {data.maturity_date && ` · Matures ${data.maturity_date}`}
            </p>
          )}
        </div>

        {/* Maturity status */}
        {maturityStatus && maturityStatus !== "current" && data?.maturity_note && (
          <div className={`rounded px-4 py-3 border text-sm font-medium ${maturityColors[maturityStatus] ?? "bg-gray-50 border-gray-200 text-gray-700"}`}>
            <span className="font-bold uppercase tracking-wide text-xs block mb-1">
              {maturityStatus === "maturing_this_year" ? "🚨 Maturing This Year" :
               maturityStatus === "within_12_months"   ? "⚠️ Matures Within 12 Months" :
               maturityStatus === "within_24_months"   ? "📅 Matures Within 24 Months" :
               maturityStatus === "past_due"            ? "⚠️ Past Due — Verify Status" : "Maturity Status"}
            </span>
            {data.maturity_note}
          </div>
        )}

        {/* Other lenders */}
        {data?.other_lenders?.length > 0 && (
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#666666] mb-2">Other Lenders / Arrangers</p>
            <div className="flex flex-wrap gap-2">
              {data.other_lenders.map((b: string, i: number) => (
                <span key={i} className="px-3 py-1 bg-gray-100 border border-gray-300 rounded-full text-xs font-semibold text-[#333333]">
                  {b}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* WF Product Advantage Panel */}
        {advantages.length > 0 && (
          <div className="border border-[#FFCD41] rounded-lg overflow-hidden">
            <button
              onClick={() => setShowAdvantages(v => !v)}
              className="w-full flex items-center justify-between px-4 py-3 bg-[#FFCD41]/20 hover:bg-[#FFCD41]/30 transition-colors"
            >
              <span className="text-sm font-bold text-[#1A1A1A] uppercase tracking-wide">
                WF vs {data?.primary_bank || "Incumbent"} — Product Comparison
              </span>
              <span className="text-xs font-bold text-[#D71E28]">{showAdvantages ? "▲ Collapse" : "▼ Expand"}</span>
            </button>

            {showAdvantages && (
              <div className="divide-y divide-gray-100">
                {advantages.map((adv: any, i: number) => (
                  <div key={i} className="px-4 py-3 flex gap-3 items-start">
                    <div className="flex-shrink-0 mt-0.5">
                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${CATEGORY_COLORS[adv.category] ?? "bg-gray-100 text-gray-700"}`}>
                        {adv.category}
                      </span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-[#1A1A1A] mb-0.5">{adv.product}</p>
                      <p className="text-xs text-[#444444] mb-1">{adv.advantage}</p>
                      {adv.incumbent_gap && (
                        <p className="text-xs text-[#D71E28] flex items-start gap-1">
                          <span className="font-bold flex-shrink-0">Gap:</span>
                          <span>{adv.incumbent_gap}</span>
                        </p>
                      )}
                    </div>
                    {adv.estimated_size && (
                      <div className="flex-shrink-0 text-right">
                        <span className="text-xs font-bold text-[#333333] bg-gray-100 px-2 py-1 rounded whitespace-nowrap">{adv.estimated_size}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Displacement strategy */}
            {data?.displacement_strategy && showAdvantages && (
              <div className="px-4 py-3 bg-[#1A1A1A] text-white">
                <p className="text-xs font-bold uppercase tracking-wide text-[#FFCD41] mb-1">Displacement Strategy</p>
                <p className="text-sm leading-relaxed">{data.displacement_strategy}</p>
              </div>
            )}
          </div>
        )}

        {/* General opportunity note */}
        {data?.opportunity && advantages.length === 0 && (
          <div className="bg-[#FFCD41]/20 border border-[#FFCD41] rounded p-3">
            <p className="text-xs font-bold uppercase tracking-wide text-[#D71E28] mb-1">WF Opportunity</p>
            <p className="text-sm text-[#333333]">{data.opportunity}</p>
          </div>
        )}

        {/* Sources */}
        {data?.sources?.length > 0 && (
          <div className="pt-2 border-t border-gray-100">
            <p className="text-[10px] font-bold uppercase tracking-wide text-[#999999] mb-1">Sources</p>
            <div className="flex flex-wrap gap-2">
              {data.sources.slice(0, 3).map((url: string, i: number) => (
                <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                  className="text-[10px] text-[#D71E28] hover:underline truncate max-w-xs">
                  {url.replace(/^https?:\/\/(www\.)?/, "")}
                </a>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
