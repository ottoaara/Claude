"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";

const ACTIVITY_TYPES = ["call", "email", "meeting", "note"] as const;
const DEAL_CATEGORIES = ["Treasury Management", "Credit & Lending", "Capital Markets", "Trade Finance", "Risk Management", "Deposits"] as const;
const DEAL_STATUSES = ["pipeline", "active", "closed", "lost"] as const;


const TYPE_COLORS: Record<string, string> = {
  call: "bg-blue-50 border-blue-300 text-blue-800",
  email: "bg-purple-50 border-purple-300 text-purple-800",
  meeting: "bg-green-50 border-green-300 text-green-800",
  note: "bg-gray-50 border-gray-300 text-gray-700",
};
const STATUS_COLORS: Record<string, string> = {
  pipeline: "bg-amber-100 text-amber-800",
  active:   "bg-green-100 text-green-800",
  closed:   "bg-blue-100 text-blue-800",
  lost:     "bg-red-100 text-red-800",
};

export default function ActivityLog({ companyName }: { companyName: string }) {
  const [activities, setActivities] = useState<any[]>([]);
  const [deals, setDeals] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"activity" | "deals">("activity");
  const [showActivityForm, setShowActivityForm] = useState(false);
  const [showDealForm, setShowDealForm] = useState(false);
  const [saving, setSaving] = useState(false);

  // Activity form state
  const [aType, setAType] = useState<string>("call");
  const [aDate, setADate] = useState(new Date().toISOString().split("T")[0]);
  const [aContact, setAContact] = useState("");
  const [aRole, setARole] = useState("");
  const [aNotes, setANotes] = useState("");
  const [aNext, setANext] = useState("");

  // Deal form state
  const [dProduct, setDProduct] = useState("");
  const [dCategory, setDCategory] = useState<string>(DEAL_CATEGORIES[0]);
  const [dStatus, setDStatus] = useState<string>("pipeline");
  const [dAmount, setDAmount] = useState("");
  const [dDate, setDDate] = useState(new Date().toISOString().split("T")[0]);
  const [dNotes, setDNotes] = useState("");

  const load = async () => {
    const [a, d] = await Promise.all([
      api.getActivities(companyName).catch(() => ({ activities: [] })),
      api.getDeals(companyName).catch(() => ({ deals: [] })),
    ]);
    setActivities(a.activities || []);
    setDeals(d.deals || []);
  };

  useEffect(() => { load(); }, [companyName]);

  const saveActivity = async () => {
    if (!aDate) return;
    setSaving(true);
    try {
      await api.addActivity(companyName, {
        type: aType, date: aDate, contact_name: aContact,
        contact_role: aRole, notes: aNotes, next_action: aNext,
      });
      setShowActivityForm(false);
      setANotes(""); setAContact(""); setARole(""); setANext("");
      await load();
    } finally { setSaving(false); }
  };

  const saveDeal = async () => {
    if (!dProduct) return;
    setSaving(true);
    try {
      await api.addDeal(companyName, {
        product: dProduct, category: dCategory, status: dStatus,
        amount: dAmount, start_date: dDate, notes: dNotes,
      });
      setShowDealForm(false);
      setDProduct(""); setDAmount(""); setDNotes("");
      await load();
    } finally { setSaving(false); }
  };

  const deleteActivity = async (id: string) => {
    await api.deleteActivity(id).catch(() => {});
    await load();
  };

  const deleteDeal = async (id: string) => {
    await api.deleteDeal(id).catch(() => {});
    await load();
  };

  const lastContact = activities[0]?.date;
  const daysSince = lastContact
    ? Math.floor((Date.now() - new Date(lastContact).getTime()) / 86400000)
    : null;

  return (
    <div className="space-y-4">
      {/* Summary header */}
      <div className="bg-white rounded-lg border-2 border-gray-200 shadow-md p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xl font-bold text-[#D71E28] border-b-2 border-[#D71E28] pb-2 uppercase tracking-wide">
            RM Activity Log
          </h3>
          <div className="flex items-center gap-4">
            {daysSince !== null && (
              <span className={`text-xs font-bold px-2 py-1 rounded ${daysSince > 60 ? "bg-red-100 text-red-700" : daysSince > 30 ? "bg-amber-100 text-amber-700" : "bg-green-100 text-green-700"}`}>
                Last contact {daysSince}d ago
              </span>
            )}
            {daysSince === null && (
              <span className="text-xs font-bold px-2 py-1 rounded bg-gray-100 text-gray-600">No contact logged</span>
            )}
          </div>
        </div>

        <div className="flex gap-6 text-center">
          <div>
            <p className="text-2xl font-black text-[#333333]">{activities.length}</p>
            <p className="text-xs text-[#666666] uppercase tracking-wide">Activities</p>
          </div>
          <div>
            <p className="text-2xl font-black text-[#333333]">{deals.filter(d => d.status === "active").length}</p>
            <p className="text-xs text-[#666666] uppercase tracking-wide">Active Deals</p>
          </div>
          <div>
            <p className="text-2xl font-black text-[#333333]">{deals.filter(d => d.status === "pipeline").length}</p>
            <p className="text-xs text-[#666666] uppercase tracking-wide">Pipeline</p>
          </div>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-2">
        {(["activity", "deals"] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-lg text-sm font-bold uppercase tracking-wide border-2 transition-colors ${
              activeTab === tab ? "bg-[#D71E28] text-white border-[#D71E28]" : "bg-white text-[#666666] border-gray-200 hover:border-[#D71E28]"
            }`}
          >
            {tab === "activity" ? `Activity (${activities.length})` : `Deals (${deals.length})`}
          </button>
        ))}
        <div className="flex-1" />
        {activeTab === "activity" && (
          <button onClick={() => setShowActivityForm(v => !v)}
            className="px-4 py-2 bg-white border-2 border-[#D71E28] text-[#D71E28] text-sm font-bold rounded-lg hover:bg-[#D71E28] hover:text-white transition-colors"
          >
            + Log Activity
          </button>
        )}
        {activeTab === "deals" && (
          <button onClick={() => setShowDealForm(v => !v)}
            className="px-4 py-2 bg-white border-2 border-[#D71E28] text-[#D71E28] text-sm font-bold rounded-lg hover:bg-[#D71E28] hover:text-white transition-colors"
          >
            + Add Deal
          </button>
        )}
      </div>

      {/* Activity form */}
      {activeTab === "activity" && showActivityForm && (
        <div className="bg-white rounded-lg border-2 border-[#D71E28] p-5 shadow-md">
          <p className="text-sm font-bold uppercase tracking-wide text-[#D71E28] mb-4">Log New Activity</p>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Type</label>
              <select value={aType} onChange={e => setAType(e.target.value)}
                className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]">
                {ACTIVITY_TYPES.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase()+t.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Date</label>
              <input type="date" value={aDate} onChange={e => setADate(e.target.value)}
                className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]" />
            </div>
            <div>
              <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Contact Name</label>
              <input value={aContact} onChange={e => setAContact(e.target.value)} placeholder="e.g. Jane Smith"
                className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]" />
            </div>
            <div>
              <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Their Role</label>
              <input value={aRole} onChange={e => setARole(e.target.value)} placeholder="e.g. CFO"
                className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]" />
            </div>
          </div>
          <div className="mb-3">
            <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Notes</label>
            <textarea value={aNotes} onChange={e => setANotes(e.target.value)} rows={3} placeholder="What was discussed?"
              className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28] resize-none" />
          </div>
          <div className="mb-4">
            <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Next Action</label>
            <input value={aNext} onChange={e => setANext(e.target.value)} placeholder="e.g. Send term sheet by Friday"
              className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]" />
          </div>
          <div className="flex gap-3">
            <button onClick={saveActivity} disabled={saving}
              className="flex-1 py-2 bg-[#D71E28] text-white font-bold rounded text-sm disabled:opacity-50 hover:bg-[#b01820] transition-colors">
              {saving ? "Saving…" : "Save Activity"}
            </button>
            <button onClick={() => setShowActivityForm(false)}
              className="flex-1 py-2 border-2 border-gray-200 text-[#666666] font-bold rounded text-sm hover:border-gray-400">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Deal form */}
      {activeTab === "deals" && showDealForm && (
        <div className="bg-white rounded-lg border-2 border-[#D71E28] p-5 shadow-md">
          <p className="text-sm font-bold uppercase tracking-wide text-[#D71E28] mb-4">Add Deal / Product</p>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="col-span-2">
              <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Product Name</label>
              <input value={dProduct} onChange={e => setDProduct(e.target.value)} placeholder="e.g. $50M Revolving Credit Facility"
                className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]" />
            </div>
            <div>
              <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Category</label>
              <select value={dCategory} onChange={e => setDCategory(e.target.value)}
                className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]">
                {DEAL_CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Status</label>
              <select value={dStatus} onChange={e => setDStatus(e.target.value)}
                className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]">
                {DEAL_STATUSES.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase()+s.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Amount / Size</label>
              <input value={dAmount} onChange={e => setDAmount(e.target.value)} placeholder="e.g. $25M"
                className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]" />
            </div>
            <div>
              <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Start / Close Date</label>
              <input type="date" value={dDate} onChange={e => setDDate(e.target.value)}
                className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28]" />
            </div>
          </div>
          <div className="mb-4">
            <label className="text-xs font-bold text-[#555555] uppercase tracking-wide">Notes</label>
            <textarea value={dNotes} onChange={e => setDNotes(e.target.value)} rows={2}
              className="w-full mt-1 border-2 border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:border-[#D71E28] resize-none" />
          </div>
          <div className="flex gap-3">
            <button onClick={saveDeal} disabled={saving || !dProduct}
              className="flex-1 py-2 bg-[#D71E28] text-white font-bold rounded text-sm disabled:opacity-50 hover:bg-[#b01820] transition-colors">
              {saving ? "Saving…" : "Save Deal"}
            </button>
            <button onClick={() => setShowDealForm(false)}
              className="flex-1 py-2 border-2 border-gray-200 text-[#666666] font-bold rounded text-sm">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Activity list */}
      {activeTab === "activity" && (
        <div className="space-y-3">
          {activities.length === 0 && (
            <div className="bg-white rounded-lg border-2 border-gray-200 p-8 text-center">
              <p className="text-[#666666]">No activities logged yet. Use "Log Activity" to track calls, emails and meetings.</p>
            </div>
          )}
          {activities.map((a, i) => (
            <div key={a.id || i} className={`bg-white rounded-lg border-2 p-4 shadow-sm ${TYPE_COLORS[a.type] || TYPE_COLORS.note}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <span className="text-xs font-bold uppercase tracking-wide px-2 py-0.5 rounded bg-gray-100 text-gray-600">{a.type}</span>
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-bold text-[#333333]">{a.date}</span>
                      {a.contact_name && <span className="text-xs font-semibold">with {a.contact_name}{a.contact_role ? ` (${a.contact_role})` : ""}</span>}
                    </div>
                    {a.notes && <p className="text-sm text-[#555555]">{a.notes}</p>}
                    {a.next_action && (
                      <p className="text-xs mt-1 font-semibold">
                        <span className="text-[#D71E28] font-bold">Next:</span> {a.next_action}
                      </p>
                    )}
                  </div>
                </div>
                {a.id && (
                  <button onClick={() => deleteActivity(a.id)} className="text-gray-400 hover:text-red-500 text-xs font-bold flex-shrink-0 uppercase">Remove</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Deals list */}
      {activeTab === "deals" && (
        <div className="space-y-3">
          {deals.length === 0 && (
            <div className="bg-white rounded-lg border-2 border-gray-200 p-8 text-center">
              <p className="text-[#666666]">No deals recorded. Add existing products or pipeline deals.</p>
            </div>
          )}
          {deals.map((d, i) => (
            <div key={d.id || i} className="bg-white rounded-lg border-2 border-gray-200 p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span className="text-sm font-bold text-[#333333]">{d.product}</span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${STATUS_COLORS[d.status] || STATUS_COLORS.pipeline}`}>
                      {d.status}
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-gray-100 rounded text-[#666666]">{d.category}</span>
                    {d.amount && <span className="text-xs font-bold text-[#D71E28]">{d.amount}</span>}
                  </div>
                  {d.start_date && <p className="text-xs text-[#888888]">{d.start_date}</p>}
                  {d.notes && <p className="text-xs text-[#555555] mt-1">{d.notes}</p>}
                </div>
                {d.id && (
                  <button onClick={() => deleteDeal(d.id)} className="text-gray-400 hover:text-red-500 text-xs font-bold flex-shrink-0 uppercase">Remove</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
