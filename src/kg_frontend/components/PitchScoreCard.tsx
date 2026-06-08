"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { GradeTooltip, ComponentTooltip } from "./ScoreTooltip";

const COMPONENTS = [
  {
    key: "timing",
    label: "Timing",
    max: 25,
    description: "How much long-term debt the company carries and how recently it filed — a proxy for refinancing opportunity.",
    higherNote: "Large debt load + fresh filing = active capital structure to compete on.",
  },
  {
    key: "covenant_stress",
    label: "Covenant Stress",
    max: 20,
    description: "Financial ratio health vs standard loan covenant thresholds (interest coverage, net margin, ROA).",
    higherNote: "Ratios approaching thresholds signal the company may need to restructure or refinance.",
  },
  {
    key: "deal_triggers",
    label: "Deal Triggers",
    max: 24,
    description: "News risk level, material events, and key concerns from the intelligence pipeline — boosted by contact gap.",
    higherNote: "High-risk news + long RM contact gap = elevated urgency on all signals.",
  },
  {
    key: "relationship_warmth",
    label: "Relationship Warmth",
    max: 16,
    description: "Board interlocks and alumni ties with WF officers, weighted by how recently those profiles were researched.",
    higherNote: "Fresh, verified connections give the RM a warm entry point into the meeting.",
  },
  {
    key: "contact_gap",
    label: "Contact Gap",
    max: 15,
    description: "Days since the RM last logged a call, email, or meeting with this company.",
    higherNote: "Longer silence = higher urgency to re-engage before a competitor does.",
  },
] as const;

const GRADE_STYLES: Record<string, string> = {
  A: "bg-green-100 text-green-800 border-green-400 ring-green-200",
  B: "bg-blue-100 text-blue-800 border-blue-400 ring-blue-200",
  C: "bg-amber-100 text-amber-800 border-amber-400 ring-amber-200",
  D: "bg-orange-100 text-orange-800 border-orange-400 ring-orange-200",
  F: "bg-gray-100 text-gray-600 border-gray-300 ring-gray-200",
};

const GRADE_LABEL: Record<string, string> = {
  A: "Strong opportunity — prioritise this week",
  B: "Good opportunity — schedule soon",
  C: "Monitor — review next quarter",
  D: "Low signal — re-research may help",
  F: "Insufficient data",
};

export default function PitchScoreCard({ companyName }: { companyName: string }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    if (!companyName) return;
    setLoading(true);
    setError(null);
    api.getPitchScore(companyName)
      .then(setData)
      .catch(() => setError("Could not load score — research this company first."))
      .finally(() => setLoading(false));
  }, [companyName]);

  if (loading) return (
    <div className="bg-white rounded-xl border-2 border-gray-200 p-5 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-40 mb-2" />
      <div className="h-8 bg-gray-200 rounded w-24" />
    </div>
  );

  if (error || !data) return (
    <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 text-sm text-gray-500">
      {error || "No score available."}
    </div>
  );

  const { score, grade, breakdown, contact_urgency } = data;
  const gradeStyle = GRADE_STYLES[grade] ?? GRADE_STYLES.F;

  return (
    <div className="bg-white rounded-xl border-2 border-gray-200 shadow-sm overflow-hidden">
      {/* Header row */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#888] mb-1">
            Pitch Opportunity Score
          </p>
          <p className="text-xs text-[#666] max-w-md">
            Deterministic score across 5 temporal signals — no AI, refreshes instantly from stored data.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <GradeTooltip grade={grade} score={score} breakdown={breakdown}>
            <div className={`flex flex-col items-center justify-center w-20 h-20 rounded-xl border-2 ring-4 ${gradeStyle}`}>
              <span className="text-3xl font-black leading-none">{score}</span>
              <span className="text-[10px] font-bold opacity-60 uppercase tracking-wide mt-0.5">/ 100</span>
              <span className="text-lg font-black mt-0.5">{grade}</span>
            </div>
          </GradeTooltip>
          <div className="text-right">
            <p className={`text-xs font-bold max-w-40 leading-tight ${
              grade === "A" ? "text-green-700" :
              grade === "B" ? "text-blue-700" :
              grade === "C" ? "text-amber-700" :
              grade === "D" ? "text-orange-700" : "text-gray-500"
            }`}>
              {GRADE_LABEL[grade] ?? ""}
            </p>
            {contact_urgency?.urgency_note && (
              <p className="text-[10px] text-[#D71E28] font-semibold mt-1 max-w-40 leading-tight">
                {contact_urgency.urgency_note}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Mini bars always visible */}
      <div className="px-6 py-4">
        <div className="space-y-2.5">
          {COMPONENTS.map(({ key, label, max }) => {
            const comp = breakdown?.[key];
            const pts = comp?.score ?? 0;
            const pct = Math.round((pts / max) * 100);
            return (
              <div key={key} className="flex items-center gap-3">
                <span className="w-36 text-xs font-semibold text-[#444] shrink-0">{label}</span>
                <ComponentTooltip componentKey={key} pct={pct} pts={pts}>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden border border-gray-200">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        pct >= 70 ? "bg-[#D71E28]" :
                        pct >= 40 ? "bg-amber-500" :
                        "bg-gray-400"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </ComponentTooltip>
                <span className="w-14 text-right text-xs shrink-0">
                  <span className="font-black text-[#333]">{pts}</span>
                  <span className="text-[#bbb]">/{max}</span>
                </span>
              </div>
            );
          })}
        </div>

        {/* Toggle detail explanation */}
        <button
          onClick={() => setShowDetail(d => !d)}
          className="mt-4 text-[11px] font-bold text-[#D71E28] hover:underline uppercase tracking-wide"
        >
          {showDetail ? "Hide explanation" : "What does each component measure?"}
        </button>

        {showDetail && (
          <div className="mt-4 space-y-3 border-t border-gray-100 pt-4">
            {COMPONENTS.map(({ key, label, max, description, higherNote }) => {
              const comp = breakdown?.[key];
              const pts = comp?.score ?? 0;
              const pct = Math.round((pts / max) * 100);
              const isHigh = pct >= 70;
              const isMid  = pct >= 40 && pct < 70;
              return (
                <div key={key} className="flex gap-3 items-start">
                  <div className={`mt-0.5 w-1.5 h-1.5 rounded-full shrink-0 mt-1.5 ${
                    isHigh ? "bg-[#D71E28]" : isMid ? "bg-amber-500" : "bg-gray-400"
                  }`} />
                  <div>
                    <p className="text-xs font-bold text-[#333]">
                      {label}
                      <span className="ml-2 text-[10px] font-normal text-[#888]">{pts}/{max} pts ({pct}%)</span>
                    </p>
                    <p className="text-[11px] text-[#666] leading-relaxed">{description}</p>
                    {isHigh && (
                      <p className="text-[11px] text-[#D71E28] font-semibold mt-0.5">{higherNote}</p>
                    )}
                    {key === "contact_gap" && comp?.days_since_contact != null && (
                      <p className="text-[11px] text-[#555] mt-0.5">
                        Last logged contact: <span className="font-bold">{comp.days_since_contact} days ago</span>
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
            <p className="text-[10px] text-[#aaa] pt-2 border-t border-gray-100">
              Score is recalculated each time you load this tab. It does not use AI — all signals come from stored research data.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
