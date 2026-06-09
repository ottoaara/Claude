"use client";

import { useState } from "react";
import { api } from "../lib/api";

interface Props {
  companyName: string;
}

export default function MeetingBrief({ companyName }: Props) {
  // Safely coerce a list item to string — Ollama sometimes returns
  // {description: "...", data_point: "..."} or {question: "..."} instead of strings
  const toStr = (item: any): string => {
    if (typeof item === "string") return item;
    if (item && typeof item === "object") {
      return (item.description || item.text || item.question ||
              item.point || item.topic || Object.values(item)[0] || "") as string;
    }
    return String(item ?? "");
  };
  const [open, setOpen] = useState(false);
  const [contactName, setContactName] = useState("");
  const [contactRole, setContactRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [brief, setBrief] = useState<any>(null);
  const [error, setError] = useState("");

  const generate = async () => {
    setLoading(true);
    setError("");
    setBrief(null);
    try {
      const result = await api.getMeetingBrief(companyName, contactName || undefined, contactRole || undefined);
      setBrief(result);
    } catch (e: any) {
      setError(e.message || "Failed to generate brief");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="px-4 py-2 bg-white border-2 border-[#FFCD41] hover:bg-[#FFCD41]/10 text-[#D71E28] text-sm font-bold rounded transition-colors"
        title="Generate pre-meeting brief"
      >
        Meeting Brief
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4" style={{background:"rgba(0,0,0,0.5)"}}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] overflow-y-auto">
            {/* Header */}
            <div className="bg-[#D71E28] px-6 py-4 rounded-t-xl flex items-center justify-between">
              <div>
                <h2 className="text-white font-black text-lg uppercase tracking-wide">Pre-Meeting Brief</h2>
                <p className="text-white/70 text-xs">{companyName}</p>
              </div>
              <button onClick={() => setOpen(false)} className="text-white/70 hover:text-white text-sm font-bold uppercase tracking-wide">Close</button>
            </div>

            <div className="p-6">
              {/* Contact inputs */}
              {!brief && (
                <div className="mb-6">
                  <p className="text-sm font-semibold text-[#333333] mb-3">Who are you meeting? (optional)</p>
                  <div className="flex gap-3">
                    <input
                      placeholder="Contact name"
                      value={contactName}
                      onChange={e => setContactName(e.target.value)}
                      className="flex-1 border-2 border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]"
                    />
                    <input
                      placeholder="Their role (e.g. CFO)"
                      value={contactRole}
                      onChange={e => setContactRole(e.target.value)}
                      className="flex-1 border-2 border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]"
                    />
                  </div>
                  {error && <p className="text-red-600 text-xs mt-2">{error}</p>}
                  <button
                    onClick={generate}
                    disabled={loading}
                    className="mt-4 w-full py-3 bg-[#D71E28] hover:bg-[#b01820] text-white font-bold rounded-lg transition-colors disabled:opacity-50"
                  >
                    {loading ? "Generating brief…" : "Generate Brief"}
                  </button>
                </div>
              )}

              {loading && (
                <div className="flex flex-col items-center py-8 gap-3">
                  <div className="w-10 h-10 border-4 border-[#D71E28] border-t-transparent rounded-full animate-spin" />
                  <p className="text-sm text-[#666666]">Synthesising intelligence across all data sources…</p>
                </div>
              )}

              {brief && (
                <div className="space-y-5">
                  {/* Headline */}
                  <div className="bg-[#D71E28] rounded-lg p-4 text-white">
                    <p className="text-xs font-bold uppercase tracking-wide opacity-70 mb-1">Why This Meeting Matters</p>
                    <p className="font-bold text-lg">{brief.headline}</p>
                  </div>

                  {/* Snapshot */}
                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <p className="text-xs font-bold uppercase tracking-wide text-[#666666] mb-2">Company Snapshot</p>
                    <p className="text-sm text-[#333333]">{brief.company_snapshot}</p>
                  </div>

                  {/* 3 + 3 */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wide text-green-700 mb-2">3 Things Going Well</p>
                      <ul className="space-y-1">
                        {(brief.three_things_going_well || []).map((t: any, i: number) => (
                          <li key={i} className="flex gap-2 text-sm text-[#333333]">
                            <span className="text-green-600 font-bold flex-shrink-0">+</span>{toStr(t)}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-xs font-bold uppercase tracking-wide text-red-700 mb-2">3 Risks to Know</p>
                      <ul className="space-y-1">
                        {(brief.three_risks || []).map((r: any, i: number) => (
                          <li key={i} className="flex gap-2 text-sm text-[#333333]">
                            <span className="text-red-600 font-bold flex-shrink-0">!</span>{toStr(r)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Likely ask */}
                  <div className="bg-amber-50 border border-amber-300 rounded-lg p-4">
                    <p className="text-xs font-bold uppercase tracking-wide text-amber-800 mb-1">Their Likely Ask</p>
                    <p className="text-sm font-semibold text-[#333333]">{brief.likely_ask}</p>
                  </div>

                  {/* Entry points */}
                  {(brief.entry_points || []).length > 0 && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <p className="text-xs font-bold uppercase tracking-wide text-blue-800 mb-2">Warm Entry Points</p>
                      <ul className="space-y-1">
                        {brief.entry_points.map((ep: any, i: number) => (
                          <li key={i} className="flex gap-2 text-sm text-[#333333]">
                            <span className="text-blue-600 flex-shrink-0 font-bold">-</span>{toStr(ep)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Smart questions */}
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wide text-[#333333] mb-2">5 Smart Questions to Ask</p>
                    <ol className="space-y-2">
                      {(brief.smart_questions || []).map((q: any, i: number) => (
                        <li key={i} className="flex gap-3 text-sm text-[#333333]">
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#D71E28] text-white text-xs font-bold flex items-center justify-center">
                            {i+1}
                          </span>
                          {toStr(q)}
                        </li>
                      ))}
                    </ol>
                  </div>

                  {/* Don't mention */}
                  {(brief.dont_mention || []).length > 0 && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-xs font-bold uppercase tracking-wide text-red-700 mb-1">Avoid Mentioning</p>
                      <ul className="space-y-1">
                        {brief.dont_mention.map((t: any, i: number) => (
                          <li key={i} className="text-xs text-red-800">• {toStr(t)}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Pre-Call Email Draft */}
                  {(brief.pre_call_email || brief.one_slide_summary) && (
                    <div className="border border-gray-300 rounded-lg overflow-hidden">
                      <div className="bg-[#1A1A1A] px-4 py-2 flex items-center justify-between">
                        <p className="text-xs font-bold uppercase tracking-widest text-[#FFCD41]">Pre-Call Email Draft</p>
                        <button
                          onClick={() => {
                            const email = brief.pre_call_email;
                            const text = email
                              ? `Subject: ${email.subject}\n\n${email.greeting}\n\n${email.body}\n\n${email.sign_off}`
                              : (brief.one_slide_summary || '');
                            navigator.clipboard?.writeText(text);
                          }}
                          className="text-xs text-gray-400 hover:text-white transition-colors px-2 py-1 rounded hover:bg-white/10"
                        >Copy</button>
                      </div>
                      <div className="bg-white p-4 space-y-3">
                        {brief.pre_call_email?.subject && (
                          <div className="flex gap-2 items-baseline border-b border-gray-100 pb-2">
                            <span className="text-xs font-bold uppercase tracking-wide text-gray-400 w-14 shrink-0">Subject</span>
                            <span className="text-sm font-semibold text-[#1A1A1A]">{brief.pre_call_email.subject}</span>
                          </div>
                        )}
                        <div className="text-sm text-[#333333] space-y-2 leading-relaxed">
                          {brief.pre_call_email ? (
                            <>
                              {brief.pre_call_email.greeting && <p className="font-medium">{brief.pre_call_email.greeting}</p>}
                              <p>{brief.pre_call_email.body}</p>
                              {brief.pre_call_email.sign_off && <p className="font-medium">{brief.pre_call_email.sign_off}</p>}
                            </>
                          ) : (
                            <p className="italic">{brief.one_slide_summary}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3 pt-2">
                    <button
                      onClick={() => { setBrief(null); setContactName(""); setContactRole(""); }}
                      className="flex-1 py-2 border-2 border-gray-300 text-[#666666] text-sm font-bold rounded-lg hover:border-[#D71E28] hover:text-[#D71E28] transition-colors"
                    >
                      New Brief
                    </button>
                    <button
                      onClick={() => setOpen(false)}
                      className="flex-1 py-2 bg-[#D71E28] text-white text-sm font-bold rounded-lg hover:bg-[#b01820] transition-colors"
                    >
                      Close
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
