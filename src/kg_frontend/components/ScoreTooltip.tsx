"use client";

import { useState, useRef, useEffect } from "react";

// ── Score rule definitions ────────────────────────────────────────────────────

export const PITCH_GRADE_RULES = {
  A: { range: "80–100", label: "Strong Opportunity", color: "text-green-700", rule: "Multiple high-urgency signals converging: material debt + covenant stress + news triggers + contact gap. Call this company this week." },
  B: { range: "60–79", label: "Good Opportunity",   color: "text-blue-700",  rule: "One or more leading indicators present. Enough signal to justify a proactive outreach within the next 30 days." },
  C: { range: "40–59", label: "Monitor",             color: "text-amber-700", rule: "Moderate signal — worth keeping on your radar. Review next quarter or after a news event." },
  D: { range: "20–39", label: "Low Signal",          color: "text-orange-700",rule: "Weak or sparse data. Re-running the research pipeline may surface new signals." },
  F: { range: "0–19",  label: "Insufficient Data",  color: "text-gray-500",  rule: "Not enough data stored to score this company. Run the research pipeline first." },
};

export const COMPONENT_RULES: Record<string, { max: number; high: string; mid: string; low: string }> = {
  timing: {
    max: 25,
    high: "Large long-term debt load with a recent filing. High probability the company is in an active capital structure cycle — refinancing, upsizing, or restructuring. Ideal for credit products.",
    mid:  "Moderate debt with a reasonably recent filing. Some refinancing potential but no acute urgency.",
    low:  "Little or no stored debt data, or filing is very old. Score will improve once EDGAR data is refreshed.",
  },
  covenant_stress: {
    max: 20,
    high: "One or more ratios are breaching or approaching covenant thresholds (interest coverage <2.5x, net margin <0%, ROA <0%). This is a financial stress signal — the company may need relief, restructuring advice, or new credit terms.",
    mid:  "Some ratios in the watch zone (e.g. coverage 2.5–3.5x, margin 0–3%). Monitor closely; deterioration could require a conversation soon.",
    low:  "All ratios are healthy. Low risk of covenant breach. Focus on growth or cross-sell rather than distress products.",
  },
  deal_triggers: {
    max: 24,
    high: "High news risk + multiple material events detected, and/or a significant contact gap is amplifying the signal. Claude has flagged this company as having active deal signals — M&A, capital raise, leadership transition, or distress.",
    mid:  "Some news signals present but at medium risk level. Worth monitoring; a new triggering event could push this higher.",
    low:  "Quiet news environment. No material events flagged. Consider whether research data is recent enough to capture current activity.",
  },
  relationship_warmth: {
    max: 16,
    high: "Fresh, verified board interlocks or alumni ties with WF officers exist. These are named warm introductions — the RM can open the conversation with a specific connection rather than a cold call.",
    mid:  "Some connections exist but profiles are aged (120–180 days old). Verify the connection is still active before referencing it.",
    low:  "No current connections found, or all officer profiles are stale. Re-running research may surface new interlocks.",
  },
  contact_gap: {
    max: 15,
    high: "No contact logged in over 90 days (or no record at all). The relationship is at risk of going cold. Combined with any other signal, this becomes the primary driver to act.",
    mid:  "30–90 days since last contact. Normal cadence slipping — schedule a touchpoint soon.",
    low:  "Recent contact within 30 days. Relationship is active; no urgency from this dimension.",
  },
};

export const URGENCY_RULES = {
  high:   "Act within 2 weeks. Claude identified a concrete, time-sensitive signal — a transaction, leadership change, or covenant breach. Delay risks a competitor getting there first. Contact gap may have elevated this from medium.",
  medium: "Act within 30 days. A real signal exists but the window is not yet closing. Use the next scheduled touchpoint or initiate a targeted outreach.",
  low:    "Monitor. Background signal only — no immediate product need identified. Flag for follow-up at the next quarterly review.",
};

export const COVENANT_RULES = {
  green:  "Ratio is comfortably within covenant limits. No immediate concern. Use as a strength point in conversations about growth financing.",
  yellow: "Ratio is in the watch zone — within 25% of breaching a standard covenant threshold. Worth raising in the next conversation; the company may already be aware.",
  red:    "Ratio has breached or is at the threshold. Standard loan covenants require action. The company may need an amendment, waiver, or new structure. High-urgency conversation topic.",
};

export const NEWS_RISK_RULES = {
  high:    "Multiple material events in the recent news cycle — earnings misses, regulatory actions, leadership departures, litigation, or M&A activity. Treat all triggers from this company as high-urgency.",
  medium:  "Some negative or significant news present but not acute. Monitor; a further development could escalate to high.",
  low:     "News environment is quiet or positive. Lower risk of distress-driven conversations; focus on growth opportunities.",
  unknown: "Insufficient news data to assess risk level. Re-run research to populate.",
};

// ── Tooltip component ─────────────────────────────────────────────────────────

interface TooltipProps {
  children: React.ReactNode;
  title: string;
  body: React.ReactNode;
  width?: string;
  position?: "top" | "bottom" | "left" | "right";
}

export function ScoreTooltip({ children, title, body, width = "w-72", position = "top" }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const anchorRef = useRef<HTMLSpanElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  function show() {
    setVisible(true);
    if (anchorRef.current) {
      const r = anchorRef.current.getBoundingClientRect();
      setCoords({
        top: position === "bottom"
          ? r.bottom + window.scrollY + 8
          : r.top + window.scrollY,
        left: r.left + window.scrollX + r.width / 2,
      });
    }
  }

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (tooltipRef.current && !tooltipRef.current.contains(e.target as Node) &&
          anchorRef.current && !anchorRef.current.contains(e.target as Node)) {
        setVisible(false);
      }
    }
    if (visible) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [visible]);

  return (
    <>
      <span
        ref={anchorRef}
        onMouseEnter={show}
        onMouseLeave={() => setVisible(false)}
        onClick={() => setVisible(v => !v)}
        className="cursor-help"
        style={{ display: "inline-flex", alignItems: "center" }}
      >
        {children}
      </span>

      {visible && (
        <div
          ref={tooltipRef}
          className={`fixed z-[9999] ${width} pointer-events-none`}
          style={{
            top: position === "bottom" ? coords.top : coords.top,
            left: coords.left,
            transform: position === "bottom"
              ? "translateX(-50%)"
              : "translateX(-50%) translateY(-100%) translateY(-8px)",
          }}
        >
          <div className="bg-[#1a1a1a] text-white rounded-lg shadow-2xl px-4 py-3 text-left">
            <p className="text-[11px] font-bold uppercase tracking-widest text-[#FFCD41] mb-1.5">{title}</p>
            <div className="text-[12px] leading-relaxed text-gray-200">{body}</div>
            <div className={`absolute left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-[#1a1a1a] rotate-45 ${
              position === "bottom" ? "-top-1.5" : "-bottom-1.5"
            }`} />
          </div>
        </div>
      )}
    </>
  );
}

// ── Convenience wrappers ──────────────────────────────────────────────────────

const BREAKDOWN_KEYS = [
  { key: "timing",             label: "Timing" },
  { key: "covenant_stress",    label: "Covenant" },
  { key: "deal_triggers",      label: "Triggers" },
  { key: "relationship_warmth",label: "Warmth" },
  { key: "contact_gap",        label: "Contact Gap" },
];

export function GradeTooltip({ grade, score, breakdown, children }: {
  grade: string;
  score?: number;
  breakdown?: Record<string, { score: number; max: number }>;
  children: React.ReactNode;
}) {
  const rule = PITCH_GRADE_RULES[grade as keyof typeof PITCH_GRADE_RULES];
  if (!rule) return <>{children}</>;

  const body = (
    <div>
      {score != null && breakdown && (
        <div className="mb-2 pb-2 border-b border-gray-700">
          {BREAKDOWN_KEYS.map(({ key, label }) => {
            const c = breakdown[key];
            if (!c) return null;
            const p = Math.round((c.score / c.max) * 100);
            return (
              <div key={key} className="flex items-center justify-between gap-4 py-0.5">
                <span className="text-gray-400 text-[11px] w-20">{label}</span>
                <div className="flex items-center gap-2">
                  <div className="w-14 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        p >= 70 ? "bg-[#D71E28]" : p >= 40 ? "bg-amber-400" : "bg-gray-500"
                      }`}
                      style={{ width: `${p}%` }}
                    />
                  </div>
                  <span className="text-[11px] font-bold text-white w-10 text-right">
                    {c.score}<span className="text-gray-500 font-normal">/{c.max}</span>
                  </span>
                </div>
              </div>
            );
          })}
          <div className="flex justify-between mt-1.5 pt-1.5 border-t border-gray-600">
            <span className="text-[11px] font-bold text-[#FFCD41]">Total</span>
            <span className="text-[11px] font-black text-[#FFCD41]">
              {score}<span className="text-gray-400 font-normal">/100</span>
            </span>
          </div>
        </div>
      )}
      <span className="text-[12px] leading-relaxed text-gray-200">{rule.rule}</span>
    </div>
  );

  return (
    <ScoreTooltip
      title={`Grade ${grade} · ${rule.range} pts · ${rule.label}`}
      body={body}
      width="w-80"
    >
      {children}
    </ScoreTooltip>
  );
}

export function ComponentTooltip({ componentKey, pct, pts, children }: {
  componentKey: string;
  pct: number;
  pts?: number;
  children: React.ReactNode;
}) {
  const rule = COMPONENT_RULES[componentKey];
  if (!rule) return <>{children}</>;
  const tier = pct >= 70 ? rule.high : pct >= 40 ? rule.mid : rule.low;
  const tierLabel = pct >= 70 ? "HIGH" : pct >= 40 ? "MID" : "LOW";
  const ptsLabel = pts != null ? `${pts}/${rule.max} pts` : `${pct}% of ${rule.max} pts max`;
  return (
    <ScoreTooltip
      title={`${tierLabel} · ${ptsLabel}`}
      body={tier}
      width="w-80"
    >
      {children}
    </ScoreTooltip>
  );
}

export function UrgencyTooltip({ urgency, children }: { urgency: string; children: React.ReactNode }) {
  const rule = URGENCY_RULES[urgency as keyof typeof URGENCY_RULES];
  if (!rule) return <>{children}</>;
  return (
    <ScoreTooltip
      title={`${urgency.toUpperCase()} Urgency`}
      body={rule}
      width="w-80"
      position="bottom"
    >
      {children}
    </ScoreTooltip>
  );
}

export function CovenantTooltip({ status, ratioLabel, value, threshold, children }: {
  status: string; ratioLabel: string; value: number | null; threshold: number; children: React.ReactNode
}) {
  const rule = COVENANT_RULES[status as keyof typeof COVENANT_RULES];
  if (!rule) return <>{children}</>;
  const valueStr = value !== null ? `Current: ${value} · Threshold: ${threshold}` : `Threshold: ${threshold}`;
  return (
    <ScoreTooltip
      title={`${ratioLabel} · ${status.toUpperCase()}`}
      body={`${valueStr}\n\n${rule}`}
      width="w-80"
      position="bottom"
    >
      {children}
    </ScoreTooltip>
  );
}

export function NewsRiskTooltip({ risk, children }: { risk: string; children: React.ReactNode }) {
  const rule = NEWS_RISK_RULES[risk as keyof typeof NEWS_RISK_RULES] ?? NEWS_RISK_RULES.unknown;
  return (
    <ScoreTooltip
      title={`News Risk: ${risk.toUpperCase()}`}
      body={rule}
      width="w-80"
      position="bottom"
    >
      {children}
    </ScoreTooltip>
  );
}
