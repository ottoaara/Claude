"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { ScoreTooltip } from "./ScoreTooltip";

// ── Wells Fargo institutional facts ──────────────────────────────────────────
const WF = {
  founded_year: 1852,
  hq_state: "California",
  hq_city: "San Francisco",
  hq_state_abbr: "CA",
  // Major WF office / presence cities (used for city-level match)
  office_cities: [
    "San Francisco", "Charlotte", "New York", "Minneapolis", "Phoenix",
    "Des Moines", "Atlanta", "Dallas", "Houston", "Los Angeles", "Chicago",
    "Denver", "Portland", "Seattle", "Salt Lake City", "Sacramento",
    "San Antonio", "Boston", "Miami", "Philadelphia", "Washington",
  ],
  // Industries WF has deep specialization in
  industry_specializations: [
    "Financial Services", "Banking", "Technology", "Healthcare",
    "Real Estate", "Energy", "Manufacturing", "Retail", "Automotive",
    "Transportation", "Logistics", "Agriculture", "Media", "Telecommunications",
    "Consumer Goods", "Pharmaceuticals", "Aerospace", "Defense",
    "Construction", "Utilities",
  ],
  // S&P 500 member
  sp500: true,
  // Public company
  public: true,
};

interface Match {
  label: string;
  detail: string;
  strength: "strong" | "moderate" | "soft";
}

interface Props {
  companyName: string;
  graphData: any; // already loaded in InsightsOverview
}

export default function WFCommonality({ companyName, graphData }: Props) {
  const [relMap, setRelMap] = useState<any>(null);
  const [relLoading, setRelLoading] = useState(true);

  useEffect(() => {
    api.getRelationshipMap(companyName)
      .then(setRelMap)
      .catch(() => setRelMap(null))
      .finally(() => setRelLoading(false));
  }, [companyName]);

  const company = graphData?.company || {};
  const matches: Match[] = [];

  // ── 1. Founded year ──────────────────────────────────────────────────
  const foundedRaw = company.founded_year ?? company.founded ?? company.year_founded;
  if (foundedRaw) {
    const yr = parseInt(String(foundedRaw));
    if (!isNaN(yr)) {
      if (yr === WF.founded_year) {
        matches.push({
          label: "Same founding year",
          detail: `Both founded in ${yr}`,
          strength: "strong",
        });
      } else if (Math.abs(yr - WF.founded_year) <= 5) {
        matches.push({
          label: "Contemporary founding",
          detail: `${companyName} founded ${yr} · WF founded ${WF.founded_year} (${Math.abs(yr - WF.founded_year)}-year gap)`,
          strength: "soft",
        });
      }
    }
  }

  // ── 2. Headquarters state ────────────────────────────────────────────
  const hq = (company.headquarters || company.hq || "").toLowerCase();
  if (hq) {
    const inCA = hq.includes("california") || hq.includes(", ca") || hq.includes("ca,") ||
                 hq.includes("san francisco") || hq.includes("los angeles") ||
                 hq.includes("san jose") || hq.includes("palo alto") || hq.includes("cupertino");
    const hqCityMatch = WF.office_cities.find(city => hq.includes(city.toLowerCase()));
    if (inCA && hq.includes("san francisco")) {
      matches.push({
        label: "Same HQ city",
        detail: `Both headquartered in San Francisco, CA`,
        strength: "strong",
      });
    } else if (inCA) {
      matches.push({
        label: "Same HQ state",
        detail: `Both headquartered in California (WF HQ: San Francisco)`,
        strength: "moderate",
      });
    } else if (hqCityMatch) {
      matches.push({
        label: "HQ in a WF hub city",
        detail: `${companyName} HQ in ${hqCityMatch} — a major Wells Fargo commercial banking market`,
        strength: "moderate",
      });
    }
  }

  // ── 3. Shared office cities ──────────────────────────────────────────
  const offices = (company.offices || company.locations || []) as string[];
  const sharedCities: string[] = [];
  for (const loc of offices) {
    const locLower = (loc || "").toLowerCase();
    const hit = WF.office_cities.find(c => locLower.includes(c.toLowerCase()));
    if (hit && !sharedCities.includes(hit)) sharedCities.push(hit);
  }
  if (sharedCities.length > 0) {
    matches.push({
      label: `${sharedCities.length} shared office ${sharedCities.length === 1 ? "city" : "cities"}`,
      detail: `Both present in: ${sharedCities.slice(0, 4).join(", ")}${sharedCities.length > 4 ? ` +${sharedCities.length - 4} more` : ""}`,
      strength: sharedCities.length >= 3 ? "strong" : "moderate",
    });
  }

  // ── 4. Industry overlap ──────────────────────────────────────────────
  const sector = (company.industry || company.sector || "").toLowerCase();
  const matchedIndustry = WF.industry_specializations.find(ind =>
    sector.includes(ind.toLowerCase()) || ind.toLowerCase().includes(sector)
  );
  if (matchedIndustry && sector) {
    matches.push({
      label: "Industry WF specialises in",
      detail: `${companyName} operates in ${matchedIndustry} — a core WF commercial banking vertical`,
      strength: "moderate",
    });
  }

  // ── 5. Public company ────────────────────────────────────────────────
  const ticker = company.ticker;
  if (ticker) {
    matches.push({
      label: "Both publicly traded",
      detail: `${companyName} (${ticker}) and Wells Fargo (WFC) are both NYSE/NASDAQ-listed companies`,
      strength: "soft",
    });
  }

  // ── 6. People connections from relationship map ──────────────────────
  if (!relLoading && relMap) {
    const boardConns = (relMap.board_connections || []) as any[];
    const alumniConns = (relMap.alumni_connections || []) as any[];

    if (boardConns.length > 0) {
      const fresh = boardConns.filter((c: any) =>
        !c.profile_freshness?.needs_refresh
      );
      const examples = boardConns
        .slice(0, 2)
        .map((c: any) => `${c.company_officer} & ${c.bank_officer} (${c.shared_board})`)
        .join("; ");
      matches.push({
        label: `${boardConns.length} shared board seat${boardConns.length > 1 ? "s" : ""}`,
        detail: examples + (fresh.length < boardConns.length ? " — some profiles may need refresh" : ""),
        strength: fresh.length > 0 ? "strong" : "moderate",
      });
    }

    if (alumniConns.length > 0) {
      const schools = [...new Set(alumniConns.map((c: any) => c.shared_school))].slice(0, 2);
      matches.push({
        label: `${alumniConns.length} shared alumni network${alumniConns.length > 1 ? "s" : ""}`,
        detail: `Common schools: ${schools.join(", ")}`,
        strength: "moderate",
      });
    }

    if (boardConns.length === 0 && alumniConns.length === 0) {
      matches.push({
        label: "No direct officer connections found",
        detail: "No shared board seats or alumni ties detected. Re-run research to check for updates.",
        strength: "soft",
      });
    }
  }

  if (matches.length === 0 && relLoading) return null;

  const strongMatches = matches.filter(m => m.strength === "strong");
  const moderateMatches = matches.filter(m => m.strength === "moderate");
  const softMatches = matches.filter(m => m.strength === "soft");

  const strengthBadge = {
    strong:   "bg-[#D71E28] text-white",
    moderate: "bg-[#FFCD41] text-[#333333]",
    soft:     "bg-gray-200 text-[#666666]",
  };

  const strengthExplain = {
    strong:   "Verified, citable fact — sourced from public records, SEC filings, or the relationship map. Safe to reference directly in a client conversation.",
    moderate: "Contextually relevant signal — use as background knowledge or a conversation opener, but verify before citing as fact.",
    soft:     "Awareness-only signal — directionally useful but not specific enough to cite. May indicate a future angle worth exploring.",
  };
  const strengthBorder = {
    strong:   "border-l-4 border-[#D71E28]",
    moderate: "border-l-4 border-[#FFCD41]",
    soft:     "border-l-4 border-gray-300",
  };

  return (
    <div className="bg-white rounded-lg p-6 border-2 border-gray-200 shadow-md">
      <h3 className="text-xl font-bold text-[#D71E28] mb-4 border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
        Wells Fargo &amp; {companyName} — What We Have in Common
      </h3>

      {relLoading && (
        <div className="flex items-center gap-2 mb-4">
          <div className="w-3 h-3 border-2 border-[#D71E28] border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-[#666666]">Checking officer connections…</span>
        </div>
      )}

      <div className="space-y-2">
        {[...strongMatches, ...moderateMatches, ...softMatches].map((m, i) => (
          <div key={i} className={`flex items-start gap-4 p-3 bg-gray-50 rounded ${strengthBorder[m.strength]}`}>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-bold text-[#333333]">{m.label}</p>
              <p className="text-xs text-[#666666] mt-0.5 leading-snug">{m.detail}</p>
            </div>
            <ScoreTooltip
              title={`${m.strength.charAt(0).toUpperCase() + m.strength.slice(1)} Connection`}
              body={strengthExplain[m.strength]}
              width="w-72"
              position="bottom"
            >
              <span className={`flex-shrink-0 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded cursor-help ${strengthBadge[m.strength]}`}>
                {m.strength}
              </span>
            </ScoreTooltip>
          </div>
        ))}
      </div>

      {!relLoading && matches.length === 0 && (
        <p className="text-sm text-[#666666]">No shared connection points detected for this company.</p>
      )}
    </div>
  );
}
