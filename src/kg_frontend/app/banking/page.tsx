"use client";

import { useState } from "react";
import CompanyResearchForm from "../../components/CompanyResearchForm";
import ResearchProgress from "../../components/ResearchProgress";
import InsightsOverview from "../../components/InsightsOverview";
import FinancialMetrics from "../../components/FinancialMetrics";
import IndustryComparison from "../../components/IndustryComparison";
import GraphVisualization from "../../components/GraphVisualization";

type ViewMode = 'summary' | 'financials' | 'industry' | 'graph';

export default function BankingKGPage() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState<string>("");
  const [researchComplete, setResearchComplete] = useState(false);
  const [researchResult, setResearchResult] = useState<any>(null);
  const [activeView, setActiveView] = useState<ViewMode>('summary');

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
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-8 py-8">
        {/* Research Form */}
        {!jobId && (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-4xl font-bold text-[#333333] mb-4">
                AI-Powered Meeting Preparation
              </h2>
              <p className="text-lg text-[#666666]">
                Research companies across 5 dimensions in under 90 seconds
              </p>
            </div>
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
                  active={activeView === 'graph'}
                  onClick={() => setActiveView('graph')}
                  label="Knowledge Graph"
                />
              </div>
            </div>

            {/* Content Views */}
            <div className="animate-fadeIn">
              {activeView === 'summary' && (
                <InsightsOverview companyName={companyName} />
              )}

              {activeView === 'financials' && (
                <FinancialMetrics
                  financials={Array.isArray(researchResult?.dimensions?.financials)
                    ? researchResult.dimensions.financials
                    : []
                  }
                />
              )}

              {activeView === 'industry' && (
                <IndustryComparison
                  industry={researchResult?.dimensions?.industry || {}}
                  companyMetrics={researchResult?.dimensions?.company_metrics}
                  industryAverages={researchResult?.dimensions?.industry_averages}
                />
              )}

              {activeView === 'graph' && (
                <GraphVisualization companyName={companyName} />
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
