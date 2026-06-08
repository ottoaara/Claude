"use client";

import { useEffect, useState } from "react";
import { api, APIError } from "../lib/api";

interface IdentifiedNeed {
  need: string;
  rationale: string;
}

interface RecommendedProduct {
  product: string;
  category: string;
  fit_score: number;
  pitch: string;
  estimated_deal_size: string;
  vs_incumbent?: string;
}

interface SalesApproach {
  primary_entry_point: string;
  key_talking_points: string[];
  meeting_agenda_suggestion: string;
  competitive_considerations: string;
}

interface RelationshipEntryPoint {
  type: "board_interlock" | "alumni";
  company_officer: string;
  connection: string;
  bank_contact: string;
  action: string;
}

interface RecommendationsData {
  company_name: string;
  customer_profile: string;
  relationship_tier: string;
  credit_assessment: string;
  identified_needs: IdentifiedNeed[];
  recommended_products: RecommendedProduct[];
  sales_approach: SalesApproach;
  relationship_entry_points: RelationshipEntryPoint[];
  risk_considerations: string[];
  next_steps: string[];
  generated_at: string;
}

interface Props {
  companyName: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  "Treasury Management": "bg-blue-50 border-blue-300 text-blue-800",
  "Credit & Lending":    "bg-green-50 border-green-300 text-green-800",
  "Capital Markets":     "bg-purple-50 border-purple-300 text-purple-800",
  "Trade Finance":       "bg-amber-50 border-amber-300 text-amber-800",
  "Risk Management":     "bg-orange-50 border-orange-300 text-orange-800",
  "Deposits":            "bg-teal-50 border-teal-300 text-teal-800",
};

const TIER_COLORS: Record<string, string> = {
  "Tier 1": "bg-[#D71E28] text-white",
  "Tier 2": "bg-orange-600 text-white",
  "Tier 3": "bg-yellow-600 text-white",
  "Tier 4": "bg-gray-500 text-white",
};

function FitScore({ score }: { score: number }) {
  const pct = (score / 10) * 100;
  const color = score >= 8 ? "bg-green-500" : score >= 6 ? "bg-yellow-500" : "bg-gray-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 rounded overflow-hidden">
        <div className={`h-full rounded ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-black text-[#333333] w-8 text-right">{score}/10</span>
    </div>
  );
}

export default function Recommendations({ companyName }: Props) {
  const [data, setData] = useState<RecommendationsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        const result = await api.getRecommendations(companyName);
        setData(result);
      } catch (err) {
        setError(err instanceof APIError ? err.message : "Failed to generate recommendations");
      } finally {
        setLoading(false);
      }
    })();
  }, [companyName]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-12 text-center border-2 border-gray-200">
        <div className="inline-block w-12 h-12 border-4 border-[#D71E28] border-t-transparent rounded-full animate-spin mb-4" />
        <p className="text-[#666666] font-semibold">Generating sales recommendations…</p>
        <p className="text-xs text-gray-400 mt-1">Synthesising financials, news, industry and officer data</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border-2 border-red-300 rounded p-8 text-red-700">
        <p className="font-bold mb-1 uppercase tracking-wide text-sm">Error</p>
        <p>{error || "No recommendation data available."}</p>
      </div>
    );
  }

  const tierKey = Object.keys(TIER_COLORS).find(t => data.relationship_tier?.startsWith(t)) ?? "Tier 4";
  const tierColor = TIER_COLORS[tierKey];

  return (
    <div className="space-y-6">

      {/* Header — Customer Profile */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <div className="flex items-start justify-between mb-4">
          <h3 className="text-xl font-bold text-[#D71E28] border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
            Sales Recommendation Brief
          </h3>
          <span className={`px-3 py-1 text-xs font-black rounded uppercase tracking-wide ${tierColor}`}>
            {data.relationship_tier}
          </span>
        </div>

        <p className="text-sm text-[#333333] bg-gray-50 border-l-4 border-[#D71E28] rounded p-4 mb-4">
          {data.customer_profile}
        </p>

        <div className="bg-yellow-50 border border-yellow-300 rounded p-3">
          <span className="text-xs font-bold uppercase tracking-wide text-yellow-800">Credit Assessment: </span>
          <span className="text-sm text-yellow-900">{data.credit_assessment}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Identified Needs */}
        <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
          <h4 className="text-base font-bold text-[#333333] uppercase tracking-wide mb-4 border-b border-gray-200 pb-2">
            Identified Needs
          </h4>
          <div className="space-y-3">
            {(data.identified_needs || []).map((need, i) => (
              <div key={i} className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#D71E28] text-white text-xs font-bold flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                <div>
                  <p className="text-sm font-bold text-[#333333]">{need.need}</p>
                  <p className="text-xs text-[#666666] mt-0.5">{need.rationale}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Considerations */}
        <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
          <h4 className="text-base font-bold text-[#333333] uppercase tracking-wide mb-4 border-b border-gray-200 pb-2">
            Risk Considerations
          </h4>
          <div className="space-y-2">
            {(data.risk_considerations || []).map((risk, i) => (
              <div key={i} className="flex gap-2 text-sm text-[#333333] bg-red-50 border border-red-200 rounded p-2">
                <span className="text-red-500 flex-shrink-0 font-bold">!</span>
                {risk}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recommended Products */}
      <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
        <h4 className="text-base font-bold text-[#333333] uppercase tracking-wide mb-4 border-b border-gray-200 pb-2">
          Recommended Wells Fargo Wholesale Products
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(data.recommended_products || [])
            .sort((a, b) => (b.fit_score ?? 0) - (a.fit_score ?? 0))
            .map((prod, i) => {
              const catClass = CATEGORY_COLORS[prod.category] ?? "bg-gray-50 border-gray-300 text-gray-700";
              return (
                <div key={i} className="border-2 border-gray-200 rounded-lg p-4 hover:border-[#D71E28] transition-colors">
                  <div className="flex items-start justify-between mb-2">
                    <p className="text-sm font-bold text-[#333333] leading-tight">{prod.product}</p>
                    <span className={`ml-2 flex-shrink-0 px-2 py-0.5 text-xs font-bold rounded border uppercase tracking-wide ${catClass}`}>
                      {prod.category}
                    </span>
                  </div>
                  <div className="mb-2">
                    <p className="text-xs text-[#666666] mb-1">Fit score</p>
                    <FitScore score={prod.fit_score ?? 0} />
                  </div>
                  <p className="text-xs text-[#333333] mb-2">{prod.pitch}</p>
                  {prod.vs_incumbent && (
                    <div className="mt-2 pt-2 border-t border-dashed border-gray-200">
                      <p className="text-[10px] font-bold uppercase tracking-wide text-[#D71E28] mb-0.5">vs Incumbent</p>
                      <p className="text-xs text-[#555555] italic">{prod.vs_incumbent}</p>
                    </div>
                  )}
                  <p className="text-xs font-bold text-[#D71E28] mt-2">{prod.estimated_deal_size}</p>
                </div>
              );
            })}
        </div>
      </div>

      {/* Sales Approach */}
      {data.sales_approach && (
        <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
          <h4 className="text-base font-bold text-[#333333] uppercase tracking-wide mb-4 border-b border-gray-200 pb-2">
            Sales Approach
          </h4>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-[#D71E28] mb-1">Primary Entry Point</p>
                <p className="text-sm text-[#333333] bg-gray-50 rounded p-3 border border-gray-200">
                  {data.sales_approach.primary_entry_point}
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-[#D71E28] mb-1">Competitive Considerations</p>
                <p className="text-sm text-[#333333] bg-gray-50 rounded p-3 border border-gray-200">
                  {data.sales_approach.competitive_considerations}
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-[#D71E28] mb-1">Suggested Meeting Agenda</p>
                <p className="text-sm text-[#333333] bg-gray-50 rounded p-3 border border-gray-200">
                  {data.sales_approach.meeting_agenda_suggestion}
                </p>
              </div>
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-[#D71E28] mb-2">Key Talking Points</p>
              <ul className="space-y-2">
                {(data.sales_approach.key_talking_points || []).map((pt, i) => (
                  <li key={i} className="flex gap-2 text-sm text-[#333333]">
                    <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#FFCD41] text-[#D71E28] text-xs font-bold flex items-center justify-center mt-0.5">
                      {i + 1}
                    </span>
                    {pt}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Relationship Entry Points */}
      {(data.relationship_entry_points || []).length > 0 && (
        <div className="bg-white rounded-lg p-6 border-2 border-[#1a5276] shadow-md">
          <div className="flex items-center justify-between mb-4 border-b border-gray-200 pb-2">
            <h4 className="text-base font-bold text-[#1a5276] uppercase tracking-wide">
              Warm Entry Points
            </h4>
            <span className="text-xs bg-[#1a5276] text-white font-bold px-2 py-1 rounded">
              {data.relationship_entry_points.length} connection{data.relationship_entry_points.length !== 1 ? "s" : ""} identified
            </span>
          </div>
          <p className="text-xs text-[#666666] mb-4">
            Existing relationships between {data.company_name} officers and Wells Fargo board members — use these for warm introductions.
          </p>
          <div className="space-y-3">
            {data.relationship_entry_points.map((ep, i) => (
              <div key={i} className={`rounded-lg p-4 border-2 ${
                ep.type === "board_interlock"
                  ? "bg-amber-50 border-amber-300"
                  : "bg-blue-50 border-blue-200"
              }`}>
                <div className="flex items-start gap-3">
                  <span className="text-xs font-bold uppercase tracking-wide px-2 py-0.5 rounded border flex-shrink-0 self-start mt-0.5 border-current opacity-60">
                    {ep.type === "board_interlock" ? "Board" : "Alumni"}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="text-sm font-bold text-[#333333]">{ep.company_officer}</span>
                      <span className="text-gray-400 text-xs">↔</span>
                      <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                        ep.type === "board_interlock" ? "bg-amber-200 text-amber-900" : "bg-blue-200 text-blue-900"
                      }`}>{ep.connection}</span>
                      <span className="text-gray-400 text-xs">↔</span>
                      <span className="text-sm font-bold text-[#D71E28]">{ep.bank_contact}</span>
                    </div>
                    <p className="text-xs text-[#555555] mt-1">{ep.action}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Next Steps */}
      <div className="bg-[#D71E28] rounded-lg p-6 text-white">
        <h4 className="text-base font-bold uppercase tracking-wide mb-4 border-b border-white/30 pb-2">
          Next Steps
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {(data.next_steps || []).map((step, i) => (
            <div key={i} className="flex gap-3 bg-white/10 rounded p-3">
              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#FFCD41] text-[#D71E28] text-xs font-black flex items-center justify-center">
                {i + 1}
              </span>
              <p className="text-sm">{step}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-white/50 mt-4 text-right">
          Generated {new Date(data.generated_at).toLocaleString()}
        </p>
      </div>

    </div>
  );
}
