"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { UrgencyTooltip } from "./ScoreTooltip";

interface Trigger {
  type: string;
  title: string;
  evidence: string;
  urgency: "high" | "medium" | "low";
  recommended_product: string;
  action: string;
}



const URGENCY_STYLES: Record<string, string> = {
  high:   "bg-red-50 border-red-400 text-red-900",
  medium: "bg-amber-50 border-amber-400 text-amber-900",
  low:    "bg-blue-50 border-blue-300 text-blue-900",
};

const URGENCY_BADGE: Record<string, string> = {
  high:   "bg-red-600 text-white",
  medium: "bg-amber-500 text-white",
  low:    "bg-blue-500 text-white",
};

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

function getCached(key: string): Trigger[] | null {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    const { data, ts } = JSON.parse(raw);
    if (Date.now() - ts > CACHE_TTL_MS) { sessionStorage.removeItem(key); return null; }
    return data;
  } catch { return null; }
}

function setCache(key: string, data: Trigger[]) {
  try { sessionStorage.setItem(key, JSON.stringify({ data, ts: Date.now() })); } catch {}
}

export default function TriggerAlerts({ companyName }: { companyName: string }) {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const cacheKey = `triggers:${companyName}`;
    const cached = getCached(cacheKey);
    if (cached) { setTriggers(cached); setLoading(false); return; }
    setLoading(true);
    api.getTriggers(companyName)
      .then(r => { const t = r.triggers || []; setCache(cacheKey, t); setTriggers(t); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [companyName]);

  if (loading) return (
    <div className="bg-white rounded-lg border-2 border-gray-200 p-5 shadow-md">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-4 h-4 border-2 border-[#D71E28] border-t-transparent rounded-full animate-spin shrink-0" />
        <p className="text-sm font-semibold text-[#555]">Analysing signals with AI&hellip;</p>
      </div>
      <p className="text-xs text-[#999]">First load takes ~30s. Result is cached for 5 minutes.</p>
    </div>
  );

  if (error) return null;

  if (triggers.length === 0) return (
    <div className="bg-white rounded-lg border-2 border-gray-200 p-5 shadow-md">
      <h4 className="text-base font-bold text-[#333333] uppercase tracking-wide mb-2">Deal Triggers</h4>
      <p className="text-sm text-[#888888]">No deal triggers detected in current data.</p>
    </div>
  );

  const high = triggers.filter(t => t.urgency === "high");
  const others = triggers.filter(t => t.urgency !== "high");

  return (
    <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md p-5">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-bold text-[#D71E28] border-b-4 border-[#D71E28] pb-2 inline-block uppercase tracking-wide">
          Deal Triggers
        </h4>
        <div className="flex gap-2">
          {high.length > 0 && (
            <span className="text-xs font-bold px-2 py-1 bg-red-600 text-white rounded animate-pulse">
              {high.length} HIGH
            </span>
          )}
          <span className="text-xs font-bold px-2 py-1 bg-gray-200 text-gray-700 rounded">
            {triggers.length} total
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {[...high, ...others].map((t, i) => (
          <div key={i} className={`rounded-lg border-2 p-4 ${URGENCY_STYLES[t.urgency]}`}>
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-sm font-bold">{t.title}</span>
                  <UrgencyTooltip urgency={t.urgency}>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide ${URGENCY_BADGE[t.urgency]}`}>
                      {t.urgency}
                    </span>
                  </UrgencyTooltip>
                  <span className="text-[10px] px-2 py-0.5 rounded border border-current opacity-60 uppercase tracking-wide">
                    {t.type}
                  </span>
                </div>
                <p className="text-xs mb-2 opacity-80">{t.evidence}</p>
                <div className="flex items-start gap-4 flex-wrap">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wide opacity-60">Recommended product</span>
                    <p className="text-xs font-semibold">{t.recommended_product}</p>
                  </div>
                  <div className="flex-1">
                    <span className="text-[10px] font-bold uppercase tracking-wide opacity-60">Next action</span>
                    <p className="text-xs font-semibold">{t.action}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
