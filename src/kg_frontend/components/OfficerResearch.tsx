"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import RelationshipMap from "./RelationshipMap";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ────────────────────────────────────────────────────────────────────
interface OfficerProfile {
  id?: string;
  name: string;
  role: string;
  role_short?: string;
  company?: string;
  profiled?: boolean;
  source_hint?: string;
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

// ─── Search link helpers ──────────────────────────────────────────────────────
function linkedInSearchUrl(name: string, company: string) {
  return `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(name + " " + company)}`;
}
function googleSearchUrl(name: string, company: string) {
  return `https://www.google.com/search?q=${encodeURIComponent('"' + name + '" ' + company)}`;
}
function bloombergSearchUrl(name: string) {
  return `https://www.bloomberg.com/search?query=${encodeURIComponent(name)}`;
}
function secEdgarSearchUrl(name: string) {
  return `https://efts.sec.gov/LATEST/search-index?q=${encodeURIComponent(name)}&dateRange=custom&startdt=2020-01-01&forms=DEF+14A`;
}

// ─── Sub-components ───────────────────────────────────────────────────────────
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
  const cls = isBoard ? "bg-purple-100 text-purple-800" : "bg-blue-100 text-blue-800";
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded uppercase tracking-wide ${cls}`}>
      {role || "Officer"}
    </span>
  );
}

function SearchLinks({ name, company }: { name: string; company: string }) {
  const links = [
    { label: "LinkedIn", href: linkedInSearchUrl(name, company), color: "text-blue-700" },
    { label: "Google",   href: googleSearchUrl(name, company),   color: "text-gray-600" },
    { label: "Bloomberg",href: bloombergSearchUrl(name),          color: "text-orange-600" },
    { label: "SEC EDGAR",href: secEdgarSearchUrl(name),           color: "text-[#D71E28]" },
  ];
  return (
    <div className="flex flex-wrap gap-2 mt-1">
      <span className="text-xs text-gray-400 font-semibold self-center">Search:</span>
      {links.map(l => (
        <a
          key={l.label}
          href={l.href}
          target="_blank"
          rel="noopener noreferrer"
          className={`text-xs font-bold ${l.color} hover:underline border border-gray-200 rounded px-1.5 py-0.5`}
        >
          {l.label}
        </a>
      ))}
    </div>
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

// ─── Unresearched stub card ───────────────────────────────────────────────────
function OfficerStubCard({ officer, onResearch, loading }: {
  officer: OfficerProfile;
  onResearch: (name: string, role: string) => void;
  loading: boolean;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3 flex items-center justify-between gap-3 shadow-sm">
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="w-7 h-7 rounded-full bg-gray-300 flex items-center justify-center text-gray-600 font-bold text-xs flex-shrink-0">
            {officer.name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase()}
          </div>
          <div>
            <p className="font-semibold text-[#333333] text-sm">{officer.name}</p>
            <p className="text-xs text-gray-500">{officer.role}</p>
          </div>
          {officer.is_board && (
            <span className="text-xs bg-purple-100 text-purple-700 font-bold px-1.5 py-0.5 rounded uppercase">Board</span>
          )}
          {officer.tenure_since && (
            <span className="text-xs text-gray-400">since {officer.tenure_since}</span>
          )}
        </div>
        <SearchLinks name={officer.name} company={officer.company || ""} />
      </div>
      <button
        onClick={() => onResearch(officer.name, officer.role)}
        disabled={loading}
        className="flex-shrink-0 text-xs px-3 py-1.5 bg-[#D71E28] hover:bg-[#b01820] text-white font-bold rounded disabled:opacity-50 transition-colors"
      >
        {loading ? "…" : "Deep Profile"}
      </button>
    </div>
  );
}

// ─── Full profile card ────────────────────────────────────────────────────────
function OfficerCard({ officer, onRefresh, refreshing }: {
  officer: OfficerProfile;
  onRefresh: (name: string, role: string) => void;
  refreshing: boolean;
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
              <div className="w-9 h-9 rounded-full bg-[#D71E28] flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                {officer.name.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase()}
              </div>
              <div>
                <p className="font-bold text-[#333333] text-sm leading-tight">{officer.name}</p>
                <p className="text-xs text-[#666666]">{officer.role}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-1">
              <RoleBadge role={officer.role_short || officer.role?.split(" ").slice(-1)[0]} isBoard={officer.is_board} />
              {officer.tenure_since && (
                <span className="text-xs text-gray-500 font-medium">Since {officer.tenure_since}</span>
              )}
              {officer.tenure_years && !officer.tenure_since && (
                <span className="text-xs text-gray-500 font-medium">{officer.tenure_years}yr tenure</span>
              )}
              <ConfidenceBadge level={officer.confidence} />
            </div>
            <SearchLinks name={officer.name} company={officer.company || ""} />
            {officer.linkedin_url && (
              <a
                href={officer.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline font-semibold mt-1 inline-block"
              >
                LinkedIn profile
              </a>
            )}
          </div>
          <button
            onClick={() => onRefresh(officer.name, officer.role)}
            disabled={refreshing}
            className="flex-shrink-0 text-xs text-[#D71E28] hover:underline font-semibold disabled:opacity-50"
          >
            {refreshing ? "…" : "Re-search"}
          </button>
        </div>

        {hasRisk && (
          <div className="mt-2 p-2 bg-red-100 border border-red-300 rounded">
            <p className="text-xs font-bold text-red-800 uppercase tracking-wide mb-1">Risk Flags</p>
            {officer.risk_flags!.map((f, i) => (
              <p key={i} className="text-xs text-red-700">• {f}</p>
            ))}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {officer.background_summary && officer.background_summary !== "Profile unavailable." && (
          <p className="text-sm text-[#333333] leading-relaxed">{officer.background_summary}</p>
        )}
        {officer.banking_relevance && (
          <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
            <p className="text-xs font-bold text-yellow-800 uppercase tracking-wide mb-0.5">Banking Relevance</p>
            <p className="text-xs text-yellow-900">{officer.banking_relevance}</p>
          </div>
        )}
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-[#D71E28] font-bold hover:underline"
        >
          {expanded ? "Less" : "Full profile"}
        </button>
        {expanded && (
          <div className="space-y-3 pt-2 border-t border-gray-100">
            <Section title="Previous Roles"          items={officer.previous_roles || []} />
            <Section title="Key Achievements"        items={officer.key_achievements || []} />
            <Section title="Recent News"             items={officer.recent_news || []} color="text-[#555555]" />
            <Section title="Publications & Speaking" items={officer.publications_speaking || []} />
            <Section title="Board Memberships"       items={officer.board_memberships || []} />
            <Section title="Education"               items={officer.education || []} />
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

  // Per-officer loading state (keyed by name)
  const [profilingName, setProfilingName] = useState<string | null>(null);

  // Manual search state
  const [searchName, setSearchName] = useState("");
  const [searchRole, setSearchRole] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Filter: all | executives | board
  const [filter, setFilter] = useState<"all" | "executives" | "board">("all");

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

  const doSearch = useCallback(async (name: string, role: string) => {
    setProfilingName(name);
    setSearchError(null);
    try {
      const res = await fetch(`${API_BASE}/officer/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, company: companyName, role: role || null }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const profile: OfficerProfile = await res.json();
      profile.profiled = true;
      setOfficers(prev => {
        const filtered = prev.filter(o => o.name.toLowerCase() !== profile.name.toLowerCase());
        return [profile, ...filtered];
      });
    } catch (e: any) {
      setSearchError(e.message);
    } finally {
      setProfilingName(null);
    }
  }, [companyName]);

  const handleManualSearch = async () => {
    if (!searchName.trim()) return;
    setSearching(true);
    setSearchError(null);
    try {
      await doSearch(searchName.trim(), searchRole.trim());
      setSearchName("");
      setSearchRole("");
    } finally {
      setSearching(false);
    }
  };

  const profiled   = officers.filter(o => o.profiled);
  const unresearched = officers.filter(o => !o.profiled);

  const visibleProfiled = profiled.filter(o =>
    filter === "all" ? true :
    filter === "board" ? o.is_board :
    !o.is_board
  );
  const visibleStubs = unresearched.filter(o =>
    filter === "all" ? true :
    filter === "board" ? o.is_board :
    !o.is_board
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg p-5 border-2 border-gray-200 shadow-md">
        <h3 className="text-2xl font-bold text-[#D71E28] mb-2 border-b-4 border-[#D71E28] pb-3 uppercase tracking-wide">
          Officer Intelligence
        </h3>
        <p className="text-sm text-[#666666] mb-4">
          Public profiles sourced from company websites, SEC proxy filings, Wikipedia, press releases, and web search.
          Use the search below to look up any named contact.
        </p>

        {/* Manual search bar */}
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-[#333333] mb-3">
            Research a specific person
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

      {/* Error / empty */}
      {!loading && (error || officers.length === 0) && (
        <div className="bg-white rounded-lg border-2 border-gray-200 p-8 text-center">
          <p className="text-[#666666] font-semibold">No officer data yet</p>
          <p className="text-xs text-gray-400 mt-1">{error ?? "Re-run research for this company, or use the search above."}</p>
        </div>
      )}

      {/* Content */}
      {!loading && officers.length > 0 && (
        <>
          {/* Summary bar + filters */}
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="text-sm text-[#666666]">
              <span className="font-bold text-[#333333]">{officers.length}</span> discovered
              {" · "}
              <span className="font-bold text-[#D71E28]">{profiled.length}</span> deep-profiled
            </div>
            <div className="flex items-center gap-2">
              {(["all", "executives", "board"] as const).map(f => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`text-xs px-3 py-1 rounded-full font-semibold border transition-colors ${
                    filter === f
                      ? "bg-[#D71E28] text-white border-[#D71E28]"
                      : "bg-white text-[#333333] border-gray-300 hover:border-[#D71E28]"
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
              <button
                onClick={fetchOfficers}
                className="text-xs text-[#D71E28] hover:underline font-bold ml-2"
              >
              Refresh
              </button>
            </div>
          </div>

          {/* Deep-profiled cards */}
          {visibleProfiled.length > 0 && (
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-[#666666] mb-3">
                Deep Profiles ({visibleProfiled.length})
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {visibleProfiled.map((o, i) => (
                  <OfficerCard
                    key={o.id || o.name + i}
                    officer={o}
                    onRefresh={(name, role) => doSearch(name, role)}
                    refreshing={profilingName === o.name}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Discovered-but-not-profiled list */}
          {visibleStubs.length > 0 && (
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-[#666666] mb-3">
                Discovered — not yet profiled ({visibleStubs.length})
                <span className="ml-2 font-normal text-gray-400 normal-case">
                  Click "Deep Profile" to research or use the search links to look them up directly
                </span>
              </p>
              <div className="space-y-2">
                {visibleStubs.map((o, i) => (
                  <OfficerStubCard
                    key={o.name + i}
                    officer={{ ...o, company: companyName }}
                    onResearch={(name, role) => doSearch(name, role)}
                    loading={profilingName === o.name}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Board Interlock Map */}
          <BoardInterlockMap companyName={companyName} />

          {/* Relationship Map: shared boards + alumni with bank officers */}
          <RelationshipMap companyName={companyName} />
        </>
      )}

      {/* These always render — they fetch independently from officer list */}
      {!loading && officers.length === 0 && (
        <>
          <BoardInterlockMap companyName={companyName} />
          <RelationshipMap companyName={companyName} />
        </>
      )}
    </div>
  );
}

// ─── Board Interlock Map ──────────────────────────────────────────────────────
interface BoardSeat {
  company: string;
  wf_officers: { name: string; role_short: string }[];
}

interface InterlockEntry {
  officer_name: string;
  officer_role: string;
  officer_role_short: string;
  board_seats: BoardSeat[];
}

interface InterlockResponse {
  interlocks: InterlockEntry[];
  shared_with_wf_count: number;
  shared_with_wf: string[];
}

function BoardInterlockMap({ companyName }: { companyName: string }) {
  const [data, setData] = useState<InterlockResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getBoardInterlocks(companyName)
      .then((res: any) => setData(res))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [companyName]);

  if (loading) return null;
  const interlocks = data?.interlocks ?? [];
  if (interlocks.length === 0) return null;

  const allCompanies = Array.from(new Set(interlocks.flatMap(d => d.board_seats.map(s => s.company))));
  const sharedCount = data?.shared_with_wf_count ?? 0;

  return (
    <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md p-5">
      <div className="flex items-start justify-between mb-1">
        <h4 className="text-lg font-bold text-[#D71E28] border-b-4 border-[#D71E28] pb-2 inline-block uppercase tracking-wide">
          Board Interlock Map
        </h4>
        {sharedCount > 0 && (
          <span className="text-xs bg-[#D71E28] text-white font-bold px-2 py-1 rounded">
            {sharedCount} shared with WF
          </span>
        )}
      </div>
      <p className="text-xs text-[#666666] mb-5">
        Officers who sit on external boards. Boards highlighted in gold are also held by a Wells Fargo officer — a direct warm introduction path.
      </p>

      <div className="space-y-4">
        {interlocks.map((entry) => (
          <div key={entry.officer_name} className="flex gap-4 items-start">
            {/* Officer pill */}
            <div className="flex-shrink-0 w-48">
              <div className="bg-[#D71E28] text-white rounded-lg px-3 py-2 text-center">
                <p className="text-xs font-bold truncate">{entry.officer_name}</p>
                <p className="text-[10px] opacity-80">{entry.officer_role_short || entry.officer_role}</p>
              </div>
            </div>

            {/* Board seats */}
            <div className="flex-1 flex items-center gap-2 flex-wrap pt-1">
              <span className="text-gray-400 text-xs font-mono">-</span>
              {entry.board_seats.map((seat, i) => {
                const wfOfficers = seat.wf_officers ?? [];
                const hasWF = wfOfficers.length > 0;
                const wfNames = wfOfficers.map((w: any) => `${w.name} (${w.role_short})`).join(", ");
                return (
                  <div key={i} className="relative group">
                    <a
                      href={`https://www.google.com/search?q=${encodeURIComponent(seat.company + " board of directors")}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        hasWF
                          ? "bg-[#FFCD41] border-2 border-[#D4A800] text-[#333333] font-bold hover:bg-yellow-300"
                          : "bg-amber-50 border border-amber-300 text-amber-900 hover:bg-amber-100"
                      }`}
                    >
                      {seat.company}
                      {hasWF && (
                        <span className="ml-1 text-[9px] font-black uppercase tracking-widest text-[#D71E28]">WF</span>
                      )}
                    </a>
                    {hasWF && (
                      <div className="absolute bottom-full left-0 mb-2 z-50 hidden group-hover:block w-64 bg-[#1a1a1a] text-white rounded-lg shadow-xl px-3 py-2 pointer-events-none">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-[#FFCD41] mb-1">WF Connection</p>
                        <p className="text-xs leading-snug">{wfNames}</p>
                        <p className="text-[10px] text-gray-400 mt-1">also sit on the {seat.company} board</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 pt-4 border-t border-gray-100 flex gap-6 text-xs text-[#666666]">
        <span><strong className="text-[#333333]">{interlocks.length}</strong> officers with external board seats</span>
        <span><strong className="text-[#333333]">{allCompanies.length}</strong> external companies</span>
        {sharedCount > 0 && (
          <span className="text-[#D71E28] font-bold"><strong>{sharedCount}</strong> shared with a WF officer</span>
        )}
      </div>
    </div>
  );
}
