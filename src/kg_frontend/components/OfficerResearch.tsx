"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────
interface OfficerProfile {
  id?: string;
  name: string;
  role: string;
  role_short?: string;
  company?: string;
  background_summary?: string;
  education?: string[];
  previous_roles?: string[];
  tenure_years?: number | null;
  tenure_since?: number | null;
  linkedin_url?: string | null;
  key_achievements?: string[];
  recent_news?: string[];
  publications_speaking?: string[];
  board_memberships?: string[];
  risk_flags?: string[];
  banking_relevance?: string;
  confidence?: string;
  is_board?: boolean;
  researched_at?: string;
  error?: string;
}

interface Props {
  companyName: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function ConfidenceBadge({ level }: { level?: string }) {
  const map: Record<string, { cls: string; label: string }> = {
    high:   { cls: "bg-green-100 text-green-800",  label: "High confidence" },
    medium: { cls: "bg-yellow-100 text-yellow-800", label: "Medium confidence" },
    low:    { cls: "bg-gray-100 text-gray-600",     label: "Low confidence" },
  };
  const { cls, label } = map[level ?? "low"] ?? map.low;
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded ${cls}`}>{label}</span>;
}

function RoleBadge({ role, isBoard }: { role?: string; isBoard?: boolean }) {
  const cls = isBoard
    ? "bg-purple-100 text-purple-800"
    : "bg-blue-100 text-blue-800";
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded uppercase tracking-wide ${cls}`}>
      {role || "Officer"}
    </span>
  );
}

function Section({ title, items, color = "text-[#333333]" }: {
  title: string; items: string[]; color?: string;
}) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <p className="text-xs font-bold uppercase tracking-wide text-[#666666] mb-1">{title}</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className={`text-sm ${color} flex items-start gap-1.5`}>
            <span className="mt-0.5 flex-shrink-0">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ─── Officer Card ─────────────────────────────────────────────────────────────
function OfficerCard({ officer, onRefresh }: {
  officer: OfficerProfile;
  onRefresh: (name: string, role: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasRisk = officer.risk_flags && officer.risk_flags.length > 0;

  return (
    <div className={`bg-white rounded-lg border-2 shadow-md overflow-hidden ${
      hasRisk ? "border-red-300" : "border-gray-200"
    }`}>
      {/* Header */}
      <div className={`p-4 ${hasRisk ? "bg-red-50" : "bg-gray-50"} border-b border-gray-200`}>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              {/* Avatar placeholder */}
              <div className="w-9 h-9 rounded-full bg-[#D71E28] flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                {officer.name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase()}
              </div>
              <div>
                <p className="font-bold text-[#333333] text-sm leading-tight">{officer.name}</p>
                <p className="text-xs text-[#666666]">{officer.role}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              <RoleBadge role={officer.role_short || officer.role?.split(" ").slice(-1)[0]} isBoard={officer.is_board} />
              {officer.tenure_since && (
                <span className="text-xs text-gray-500 font-medium">
                  Since {officer.tenure_since}
                </span>
              )}
              {officer.tenure_years && (
                <span className="text-xs text-gray-500 font-medium">
                  {officer.tenure_years}yr tenure
                </span>
              )}
              <ConfidenceBadge level={officer.confidence} />
            </div>
          </div>
          <div className="flex flex-col gap-1 flex-shrink-0">
            {officer.linkedin_url && (
              <a
                href={officer.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline font-semibold"
              >
                LinkedIn ↗
              </a>
            )}
            <button
              onClick={() => onRefresh(officer.name, officer.role)}
              className="text-xs text-[#D71E28] hover:underline font-semibold"
            >
              Re-search
            </button>
          </div>
        </div>

        {/* Risk flags — always visible */}
        {hasRisk && (
          <div className="mt-2 p-2 bg-red-100 border border-red-300 rounded">
            <p className="text-xs font-bold text-red-800 uppercase tracking-wide mb-1">⚠ Risk Flags</p>
            {officer.risk_flags!.map((f, i) => (
              <p key={i} className="text-xs text-red-700">• {f}</p>
            ))}
          </div>
        )}
      </div>

      {/* Background summary */}
      <div className="p-4 space-y-3">
        {officer.background_summary && officer.background_summary !== "Profile unavailable." && (
          <p className="text-sm text-[#333333] leading-relaxed">{officer.background_summary}</p>
        )}

        {/* Banking relevance highlight */}
        {officer.banking_relevance && (
          <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-xs font-bold text-yellow-800 uppercase tracking-wide mb-0.5">Banking Relevance</p>
            <p className="text-xs text-yellow-900">{officer.banking_relevance}</p>
          </div>
        )}

        {/* Expand / collapse */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-[#D71E28] font-bold hover:underline"
        >
          {expanded ? "▲ Less detail" : "▼ Full profile"}
        </button>

        {expanded && (
          <div className="space-y-3 pt-2 border-t border-gray-100">
            <Section title="Previous Roles" items={officer.previous_roles || []} />
            <Section title="Key Achievements" items={officer.key_achievements || []} />
            <Section
              title="Recent News"
              items={officer.recent_news || []}
              color="text-[#555555]"
            />
            <Section title="Publications & Speaking" items={officer.publications_speaking || []} />
            <Section title="Board Memberships" items={officer.board_memberships || []} />
            <Section title="Education" items={officer.education || []} />
            {officer.researched_at && (
              <p className="text-xs text-gray-400">
                Researched: {new Date(officer.researched_at).toLocaleString()}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function OfficerResearch({ companyName }: Props) {
  const [officers, setOfficers] = useState<OfficerProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Manual search state
  const [searchName, setSearchName] = useState("");
  const [searchRole, setSearchRole] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const fetchOfficers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/company/${encodeURIComponent(companyName)}/officers`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setOfficers(data.officers || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (companyName) fetchOfficers();
  }, [companyName]);

  const handleManualSearch = async () => {
    if (!searchName.trim()) return;
    setSearching(true);
    setSearchError(null);
    try {
      const res = await fetch(`${API_BASE}/officer/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: searchName.trim(),
          company: companyName,
          role: searchRole.trim() || null,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const profile: OfficerProfile = await res.json();
      // Merge into list (replace if same name, else prepend)
      setOfficers(prev => {
        const filtered = prev.filter(o => o.name.toLowerCase() !== profile.name.toLowerCase());
        return [profile, ...filtered];
      });
      setSearchName("");
      setSearchRole("");
    } catch (e: any) {
      setSearchError(e.message);
    } finally {
      setSearching(false);
    }
  };

  const handleRefresh = async (name: string, role: string) => {
    setSearchName(name);
    setSearchRole(role);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-5 border-2 border-gray-200 shadow-md">
        <h3 className="text-2xl font-bold text-[#D71E28] mb-2 border-b-4 border-[#D71E28] pb-3 uppercase tracking-wide">
          Officer Intelligence
        </h3>
        <p className="text-sm text-[#666666] mb-4">
          Professional profiles on key executives, sourced from web search, news, and public filings.
          Use the search below if your contact isn't in the auto-discovered list.
        </p>

        {/* Manual search bar */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-[#333333] mb-3">
            Search for a specific person
          </p>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              placeholder="Full name (e.g. Jane Smith)"
              value={searchName}
              onChange={e => setSearchName(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleManualSearch()}
              className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm text-[#333333] focus:outline-none focus:border-[#D71E28]"
            />
            <input
              type="text"
              placeholder="Role (optional, e.g. CFO)"
              value={searchRole}
              onChange={e => setSearchRole(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleManualSearch()}
              className="w-48 border border-gray-300 rounded px-3 py-2 text-sm text-[#333333] focus:outline-none focus:border-[#D71E28]"
            />
            <button
              onClick={handleManualSearch}
              disabled={searching || !searchName.trim()}
              className="px-5 py-2 bg-[#D71E28] hover:bg-[#b01820] text-white font-bold rounded text-sm disabled:opacity-50 transition-colors"
            >
              {searching ? "Searching…" : "Research"}
            </button>
          </div>
          {searchError && (
            <p className="text-xs text-red-600 mt-2">Error: {searchError}</p>
          )}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-white rounded-lg border-2 border-gray-200 p-8 text-center">
          <div className="animate-pulse text-[#D71E28] font-semibold">Loading officer profiles…</div>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="bg-white rounded-lg border-2 border-gray-200 p-6 text-center">
          <p className="text-[#666666] font-semibold">No officer data yet</p>
          <p className="text-xs text-gray-400 mt-1">{error}</p>
          <p className="text-xs text-gray-400 mt-1">
            Officer profiles are built automatically when you run research — or use the search above.
          </p>
        </div>
      )}

      {/* Officer grid */}
      {!loading && !error && officers.length === 0 && (
        <div className="bg-white rounded-lg border-2 border-gray-200 p-8 text-center">
          <p className="text-[#666666] font-semibold">No officer profiles found</p>
          <p className="text-xs text-gray-400 mt-1">
            Re-run research for this company, or use the search above to look up a specific person.
          </p>
        </div>
      )}

      {!loading && officers.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-[#666666]">
              {officers.length} officer{officers.length !== 1 ? "s" : ""} profiled
            </p>
            <button
              onClick={fetchOfficers}
              className="text-xs text-[#D71E28] hover:underline font-bold"
            >
              ↺ Refresh
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {officers.map((officer, i) => (
              <OfficerCard
                key={officer.id || officer.name + i}
                officer={officer}
                onRefresh={handleRefresh}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
