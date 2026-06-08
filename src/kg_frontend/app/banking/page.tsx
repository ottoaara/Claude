"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "../../lib/api";
import CompanyResearchForm from "../../components/CompanyResearchForm";
import ResearchProgress from "../../components/ResearchProgress";
import InsightsOverview from "../../components/InsightsOverview";
import FinancialMetrics from "../../components/FinancialMetrics";
import IndustryComparison from "../../components/IndustryComparison";
import PeerComparison from "../../components/PeerComparison";
import GraphVisualization from "../../components/GraphVisualization";
import NewsAnalysis from "../../components/NewsAnalysis";
import OfficerResearch from "../../components/OfficerResearch";
import Recommendations from "../../components/Recommendations";
import TriggerAlerts from "../../components/TriggerAlerts";
import CovenantWatch from "../../components/CovenantWatch";
import IncumbentBank from "../../components/IncumbentBank";
import MeetingBrief from "../../components/MeetingBrief";
import ActivityLog from "../../components/ActivityLog";
import PitchScoreCard from "../../components/PitchScoreCard";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ViewMode = 'summary' | 'financials' | 'industry' | 'news' | 'graph' | 'officers' | 'recommendations' | 'activity';

export default function BankingKGPageWrapper() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-50 flex items-center justify-center"><div className="w-10 h-10 border-4 border-[#D71E28] border-t-transparent rounded-full animate-spin" /></div>}>
      <BankingKGPage />
    </Suspense>
  );
}

function BankingKGPage() {
  const searchParams = useSearchParams();
  const [jobId, setJobId] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState<string>("");
  const [researchComplete, setResearchComplete] = useState(false);
  const [researchResult, setResearchResult] = useState<any>(null);
  const [activeView, setActiveView] = useState<ViewMode>('summary');
  const [pdfDownloading, setPdfDownloading] = useState(false);
  const [windowConfig, setWindowConfig] = useState({ fin_window: 365, news_window: 90, prod_window: 730 });

  // Company picker
  const [savedCompanies, setSavedCompanies] = useState<{ name: string; ticker: string; industry: string }[]>([]);
  useEffect(() => {
    api.getCompanies().then(setSavedCompanies).catch(() => {});
  }, []);

  // Auto-load company from URL ?company= param
  useEffect(() => {
    const co = searchParams?.get("company");
    if (co && !jobId) handleLoadCompany(co);
  }, [searchParams]);

  const handleLoadCompany = async (name: string) => {
    setCompanyName(name);
    setJobId("loaded");
    setActiveView('summary');
    try {
      const graph = await fetch(
        `${API_BASE}/company/${encodeURIComponent(name)}/graph`
      ).then(r => r.json());

      // Unpack data_json for each financial record — Neo4j stores root-level
      // fields with "Unknown" period; the real values are inside data_json.
      const financials = (graph.financials || []).map((f: any) => {
        try {
          const inner = typeof f.data_json === "string" ? JSON.parse(f.data_json) : (f.data_json || {});
          const innerInner = typeof inner.data_json === "string" ? JSON.parse(inner.data_json) : (inner.data_json || {});
          return { ...innerInner, ...inner, ...f, data_json: undefined,
            period: innerInner.filing_period || inner.period || f.period || "Unknown" };
        } catch { return f; }
      });

      setResearchResult({
        dimensions: {
          financials,
          industry: graph.industries?.[0] || {},
          company_info: graph.company || {},
          news: graph.news || [],
          products: graph.products || [],
        },
        summary: graph.company?.summary || "",
        completed_steps: [],
        errors: [],
      });
    } catch {
      setResearchResult({ dimensions: {}, summary: "", completed_steps: [], errors: [] });
    }
    setResearchComplete(true);
  };

  const handleDownloadPdf = async () => {
    if (!companyName) return;
    setPdfDownloading(true);
    try {
      const res = await fetch(
        `${API_BASE}/company/${encodeURIComponent(companyName)}/report/pdf`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      a.download = `${companyName.replace(/\s+/g, "_")}_intelligence_brief.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("PDF generation failed. Check backend logs.");
    } finally {
      setPdfDownloading(false);
    }
  };

  const handleResearchStart = (newJobId: string, company: string) => {
    setJobId(newJobId);
    setCompanyName(company);
    setResearchComplete(false);
    setResearchResult(null);
  };

  const handleResearchComplete = (result: any) => {
    console.log('Research completed with result:', result);
    console.log('Financials:', result?.dimensions?.financials);
    console.log('Industry:', result?.dimensions?.industry);
    setResearchComplete(true);
    setResearchResult(result);
  };

  const handleNewResearch = () => {
    setJobId(null);
    setCompanyName("");
    setResearchComplete(false);
    setResearchResult(null);
    setActiveView('summary');
    api.getCompanies().then(setSavedCompanies).catch(() => {});
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Wells Fargo Header */}
      <header className="bg-[#D71E28] border-b-4 border-[#FFCD41] sticky top-0 z-50 shadow-md">
        <div className="max-w-7xl mx-auto px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-3 border-r-2 border-[#FFCD41] pr-4">
                  <span className="text-3xl font-bold text-[#FFCD41]">WELLS FARGO</span>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-white">Commercial Banking</h1>
                  <p className="text-xs text-[#FFCD41] tracking-wide uppercase">
                    Client Intelligence Platform
                  </p>
                </div>
              </div>
            </div>
            {researchComplete && (
              <button
                onClick={handleNewResearch}
                className="px-6 py-3 bg-[#FFCD41] hover:bg-[#FFD966] text-[#D71E28] rounded font-bold transition-all shadow-lg border-2 border-white"
              >
                + New Research
              </button>
            )}
            <div className="flex items-center gap-3">
              <Link href="/rm" className="px-4 py-2 bg-white/20 hover:bg-white/30 text-white text-sm font-bold rounded border border-white/40 transition-colors">
                Portfolio
              </Link>
              {researchComplete && companyName && (
                <MeetingBrief companyName={companyName} />
              )}
              {researchComplete && companyName && (
                <button
                  onClick={handleDownloadPdf}
                  disabled={pdfDownloading}
                  className="px-6 py-3 bg-white hover:bg-gray-100 text-[#D71E28] rounded font-bold transition-all shadow-lg border-2 border-white disabled:opacity-60"
                >
                  {pdfDownloading ? "Generating PDF…" : "Export PDF"}
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-8 py-8">
        {/* Research Form */}
        {!jobId && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-4xl font-bold text-[#333333] mb-4">
                Commercial CFF Demo
              </h2>
              <p className="text-lg text-[#666666]">
                Where Context Meets Signal
              </p>
            </div>

            {/* Previously researched companies */}
            {savedCompanies.length > 0 && (
              <div className="mb-4 flex items-center gap-3">
                <label className="text-xs font-bold text-[#666666] uppercase tracking-widest whitespace-nowrap">Load existing</label>
                <select
                  defaultValue=""
                  onChange={(e) => { if (e.target.value) handleLoadCompany(e.target.value); }}
                  className="flex-1 px-3 py-2 border-2 border-gray-200 hover:border-[#FFCD41] rounded-lg text-sm text-[#333333] bg-white focus:outline-none focus:border-[#D71E28] cursor-pointer"
                >
                  <option value="" disabled>— pick a company —</option>
                  {savedCompanies.map((c, i) => (
                    <option key={`${c.name}-${i}`} value={c.name}>
                      {c.name}{c.ticker ? ` (${c.ticker})` : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <CompanyResearchForm onResearchStart={handleResearchStart} />
          </div>
        )}

        {/* Research Progress */}
        {jobId && !researchComplete && (
          <ResearchProgress
            jobId={jobId}
            companyName={companyName}
            onComplete={handleResearchComplete}
          />
        )}

        {/* Research Results */}
        {researchComplete && companyName && researchResult && (
          <div className="space-y-6">
            {/* Navigation Tabs - Wells Fargo Style */}
            <div className="bg-white rounded-lg shadow-md border-2 border-gray-200">
              <div className="flex border-b-2 border-gray-200">
                <TabButton
                  active={activeView === 'summary'}
                  onClick={() => setActiveView('summary')}
                  label="Executive Summary"
                />
                <TabButton
                  active={activeView === 'financials'}
                  onClick={() => setActiveView('financials')}
                  label="Financial Metrics"
                />
                <TabButton
                  active={activeView === 'industry'}
                  onClick={() => setActiveView('industry')}
                  label="Industry Analysis"
                />
                <TabButton
                  active={activeView === 'news'}
                  onClick={() => setActiveView('news')}
                  label="News & Sentiment"
                />
                <TabButton
                  active={activeView === 'graph'}
                  onClick={() => setActiveView('graph')}
                  label="Knowledge Graph"
                />
                <TabButton
                  active={activeView === 'officers'}
                  onClick={() => setActiveView('officers')}
                  label="Officer Intelligence"
                />
                <TabButton
                  active={activeView === 'recommendations'}
                  onClick={() => setActiveView('recommendations')}
                  label="Pitch"
                />
                <TabButton
                  active={activeView === 'activity'}
                  onClick={() => setActiveView('activity')}
                  label="Activity"
                />
              </div>
            </div>

            {/* Content Views */}
            <div className="animate-fadeIn">
              {activeView === 'summary' && (
                <div className="space-y-4">
                  <TriggerAlerts companyName={companyName} />
                  <InsightsOverview companyName={companyName} />
                </div>
              )}

              {activeView === 'financials' && (
                <div className="space-y-4">
                  <CovenantWatch companyName={companyName} />
                  <FinancialMetrics companyName={companyName} />
                </div>
              )}

              {activeView === 'industry' && (
                <div className="space-y-6">
                  <IndustryComparison
                    industry={researchResult?.dimensions?.industry || {}}
                    companyMetrics={researchResult?.dimensions?.company_metrics}
                    industryAverages={researchResult?.dimensions?.industry_averages}
                  />
                  <PeerComparison companyName={companyName} />
                </div>
              )}

              {activeView === 'news' && (
                <NewsAnalysis
                  companyName={companyName}
                  ticker={researchResult?.dimensions?.company_info?.ticker || undefined}
                  newsWindowDays={windowConfig.news_window}
                  onWindowChange={setWindowConfig}
                />
              )}

              {activeView === 'graph' && (
                <GraphVisualization companyName={companyName} />
              )}

              {activeView === 'officers' && (
                <OfficerResearch companyName={companyName} />
              )}

              {activeView === 'recommendations' && (
                <div className="space-y-4">
                  <PitchScoreCard companyName={companyName} />
                  <IncumbentBank companyName={companyName} />
                  <Recommendations companyName={companyName} />
                </div>
              )}

              {activeView === 'activity' && (
                <ActivityLog companyName={companyName} />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  label
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 px-6 py-4 font-bold transition-all border-b-4 text-sm uppercase tracking-wide ${
        active
          ? 'bg-white border-[#D71E28] text-[#D71E28]'
          : 'bg-gray-50 border-transparent text-[#666666] hover:bg-gray-100'
      }`}
    >
      {label}
    </button>
  );
}
